import json
import os

from app import logger
from app import util as app_utils
from app.config import Config
from app.convertkit.ck_api import ConvertKitApi
from app.convertkit.ck_ui import ConvertKitUi
from app.less_annoying_crm.lac_api import LacApi
from app.less_annoying_crm.lac_ui import LacUI


class Lac:
    def __init__(self, timeout=15):
        self.lac_ui = LacUI()
        self.lac_api = LacApi()
        self.ck_ui = ConvertKitUi()
        self.ck_api = ConvertKitApi()
        self.timeout = timeout
        self.new_user_data = []  # to be added once checking for any new users

    def save_any_new_lac_users(self):
        curr_users = self.lac_api.get_all_contacts()

        if os.path.isfile(Config.LAC_PREV_USERS_PATH):
            prev_users = self.get_prev_lac_users()

            prev_user_emails = []
            curr_user_emails = []
            for curr in curr_users:
                e = curr["email"].lower()
                curr_user_emails.append(e)  # make sure right key
            for prev in prev_users:
                e = prev["email"].lower()
                prev_user_emails.append(e)

            for curr in curr_users:
                if curr["email"].lower() not in prev_user_emails:
                    curr["email"] = curr["email"].lower()
                    self.new_user_data.append(curr)
        else:
            logger.info("No prev LAC users file")

        logger.info("Archiving curr users for next time")
        app_utils.archive_curr_users(file=Config.LAC_PREV_USERS_PATH,
                                     curr_users=curr_users)

    def get_prev_lac_users(self):
        with open(Config.LAC_PREV_USERS_PATH, "r") as prev_lac_f:
            raw_prev_users = prev_lac_f.read()
        prev_users = json.loads(raw_prev_users)
        return prev_users

    def create_new_lac_user(self, users_info):
        """
        Called by other systems (Acuity, ConvertKit)

        Uses LessAnnoying CRM API to create new users (with group & note)

        """
        logger.info("Adding new user(s) to LessAnnoying CRM ...")

        for user in users_info:
            if not self.lac_api.user_exists(email=user["email"]):
                lac_user_id = self.lac_api.create_new_user(user_data=user)
                self.lac_api.add_user_to_group(user_id=lac_user_id, group_name=Config.LAC_NEW_USER_GROUP_NAME)

                if user["note"]:
                    self.lac_api.add_note_to_user(lac_user_id=lac_user_id, note=user["note"])
                else:
                    logger.warning("No note provided for user")

                app_utils.write_to_changelog(f"Created LAC user: {user['email']}")

        # TODO update prev_lac file (after converting to JSON

    def add_any_new_users_to_convertkit(self):
        logger.info("""
        *******************************
        Syncing 
            Less Annoying CRM --> ConvertKit
        *******************************
        """)

        logger.info("Checking if any new LAC users ...")
        self.save_any_new_lac_users()

        if self.new_user_data:
            logger.info("New LAC users found. Checking if new LAC users already exist in ConvertKit...")

            new_ck_users = []
            for new_lac_user in self.new_user_data:
                user = {
                    "first_name": new_lac_user["first_name"],
                    "email": new_lac_user["email"]
                }
                new_ck_users.append(user)

            self.ck_ui.add_users_to_ck(users_info=new_ck_users)


# Old way to getting curr/prev users with XLS and CSV files
"""
import os
import shutil
import time
import csv
import xlrd
from csv_diff import compare, load_csv
from xlrd.timemachine import xrange

    def get_any_new_lac_users_ui_not_used(self):
        ###################
        # export from LAC #
        ###################
        self.lac_ui.login()
        self.lac_ui.export_current_contacts()

        time.sleep(Config.LAC_EXPORT_WAIT_TIME_SEC_SHORT)

        xls_path = util.get_xls_path(search_dir=Config.DOWNLOADS_DIR)

        prev_contacts_csv = Config.LAC_PREV_USERS_PATH
        curr_contacts_csv = self._convert_xls_to_csv(xls_path)

        added, removed = self._get_added_and_removed_contacts(prev_csv=prev_contacts_csv, curr_csv=curr_contacts_csv)
        self.archive_downloaded_csv()

        ####################
        # get unique lists #
        ####################
        added_emails = []
        removed_emails = []

        for a in added:
            added_emails.append(a["email"])
        for r in removed:
            removed_emails.append(r["email"])

        ###########
        # compare #
        ###########
        new_user_data = []

        for added_em in added_emails:
            if added_em not in removed_emails:
                logger.info(f"New LAC user found ({added_em}). Saving user data ...")

                # find user info and save #
                for a in added:
                    if a["email"] == added_em:
                        new_user_data.append({
                            "first_name": a["first_name"],
                            "email": a["email"]
                        })

        if not new_user_data:
            logger.info("No new LAC users found")

        self.new_user_data = new_user_data

    def _convert_xls_to_csv(self, xls_path):

        wb = xlrd.open_workbook(xls_path)
        sh = wb.sheet_by_index(0)  # all data in first (and only) sheet as of Mar 2020

        lac_csv = open(Config.LAC_CURR_PATH, 'w')
        wr = csv.writer(lac_csv, quoting=csv.QUOTE_ALL)

        for rownum in xrange(sh.nrows):
            wr.writerow(sh.row_values(rownum))

        lac_csv.close()
        return Config.LAC_CURR_PATH

    def _get_added_and_removed_contacts(self, prev_csv, curr_csv):
        if not os.path.isfile(prev_csv):
            # just make copy to avoid FNF erro
            shutil.copyfile(curr_csv, prev_csv)

        compare_out = compare(
            load_csv(open(prev_csv)),
            load_csv(open(curr_csv))
        )

        added_data = []
        removed_data = []

        for added in compare_out["added"]:
            if added["First Name"] and added["Primary Email"]:
                added_data.append({"email": added["Primary Email"],
                                   "first_name": added["First Name"]})

        for removed in compare_out["removed"]:
            if removed["First Name"] and removed["Primary Email"]:
                removed_data.append({"email": removed["Primary Email"],
                                     "first_name": removed["First Name"]})

        return added_data, removed_data

    def archive_downloaded_csv(self):
        logger.info("Archiving (renaming) LAC users ...")
        os.rename(src=Config.LAC_CURR_PATH, dst=Config.LAC_PREV_USERS_PATH)
"""
