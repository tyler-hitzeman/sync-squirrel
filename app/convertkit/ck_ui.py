import time
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from app import logger, driver, wait, ec, util
from app.config import Config
from app.convertkit.ck_api import ConvertKitApi
from app.convertkit import util


class ConvertKitUi:
    def __init__(self, sequences=Config.CONVERT_SEQ, max_retries=10):
        self.ck_api = ConvertKitApi()
        self.sequences = sequences
        self.max_retries = max_retries

    def login(self, username, password):
        logger.info("Logging in ...")
        driver.get("https://app.convertkit.com/users/login")

        username_elem = driver.find_element_by_id("user_email")
        password_elem = driver.find_element_by_id("user_password")

        username_elem.send_keys(username)
        password_elem.send_keys(password)

        submit_btn = "/html/body/div[1]/div/div[2]/div[2]/div/div/div[2]/form/button"
        driver.find_element_by_xpath(submit_btn).click()

    def add_users_to_ck(self, users_info):

        # TODO remove bool if unneeded
        logged_in = False

        if logged_in is False:
            self.login(username=Config.CONVERT_USER, password=Config.CONVERT_PW)
            logged_in = True

        for user in users_info:
            if not self.ck_api.user_exists(user_email=user["email"]):
                first_name = user["first_name"]
                email = user["email"]
                logger.info(f"Adding CK subscriber ({email})...")

                try:
                    wait.until(ec.visibility_of_all_elements_located)
                    wait.until(ec.presence_of_all_elements_located)
                    time.sleep(5)

                    self._click_add_subs_home_btn()
                    self._click_add_single_sub_btn(first_name=first_name, email=email)
                    self._enter_name_and_email(first_name=first_name, email=email)
                    self._click_sequences_dropdown()
                    self._click_sequences_checkboxes()
                    self._click_save_subscriber_btn()

                except Exception as e:
                    logger.exception(e)
                    print("sleeping before quitting ...")
                    time.sleep(10)
                    driver.quit()

        # keep hist users file up-to-date
        curr_users = self.ck_api.get_current_convertkit_users()
        util.save_users_to_prev_users_file(users=curr_users)

    def _click_add_subs_home_btn(self):
        logger.info("Clicking Add Subscribers button ...")
        try:
            # try getting elem by id?
            add_subs_btn = driver.find_element_by_css_selector(".break > div:nth-child(1) > a:nth-child(1)")
            add_subs_btn.click()
        except (NoSuchElementException, TimeoutException) as ne:
            logger.info(f"\nretrying..\n")
            self._click_add_subs_home_btn()

    def _click_add_single_sub_btn(self, first_name, email):
        # TODO add check to make sure user doesn't already exist - otherwise can't save

        logger.info("Clicking Add Single Subscriber button ...")

        curr_retry_count = 0
        if curr_retry_count < self.max_retries:

            try:
                time.sleep(4)
                driver.implicitly_wait(10)  # explicit driver wait wasnt working for single sub btn

                # this alone didnt fix, needed sleep
                # single_sub_btn = wait.until(ec.element_to_be_clickable((By.CLASS_NAME, "btn--step--single-sub")))
                single_sub_btn = driver.find_element_by_class_name("btn--step--single-sub")  # orig, worked but fickle
                print("***\nFound Single Sub Button\n***")
                single_sub_btn.click()
                print("!!! clicked singl sub button !!!")
                time.sleep(2)

            except (NoSuchElementException, TimeoutException) as ne:
                curr_retry_count += 1
                logger.info(f"Retrying after {repr(ne)}..")
                time.sleep(2)
                self._click_add_single_sub_btn(first_name, email)

    def _enter_name_and_email(self, first_name, email):
        try:
            ########################
            # enter name and email #
            ########################
            # wait(ec.presence_of_all_elements_located)
            driver.implicitly_wait(10)
            # first_name_element = wait.until(ec.element_located_to_be_selected((By.ID, 'first-name')))  # testing
            print('\n**located first name elem**\n')

            first_name_element = driver.find_element_by_id("first-name")  # orig, broke
            email_element = driver.find_element_by_id("email")

            #####################
            # add subscriber(s) #
            #####################
            first_name_element.clear()
            first_name_element.send_keys(first_name)
            email_element.send_keys(email)

        except (NoSuchElementException, TimeoutException) as ne:
            logger.info(f"\nFailed entering name & email. Trying again ...\n")
            time.sleep(1)
            self._enter_name_and_email(first_name, email)

    def _click_sequences_dropdown(self):
        try:
            # find Sequences dropdown
            all_em_elems = driver.find_elements_by_tag_name("em")
            reasonable_opts = []
            for em_elem in all_em_elems:
                if "0 of " in em_elem.text:
                    reasonable_opts.append(em_elem)

            # click dropdown
            sequences_dropdown = reasonable_opts[1]  # 0 = Forms; 1 = Sequences; 2 = Tags
            sequences_dropdown.click()

        except (NoSuchElementException, TimeoutException) as ne:
            logger.info(f"\nFailed clicking sequences dropdown. Trying again ...\n")
            time.sleep(1)
            self._click_sequences_dropdown()

    def _click_sequences_checkboxes(self):
        try:
            # click sequence checkbox
            label_elems = driver.find_elements_by_tag_name("label")
            for label in label_elems:
                for seq_name in self.sequences:
                    if seq_name in label.text:
                        label.click()
                        break
        except (NoSuchElementException, TimeoutException) as ne:
            logger.info(f"\nFailed clicking sequences checkboxes. Trying again ...\n")
            time.sleep(1)
            self._click_sequences_checkboxes()

    def _click_save_subscriber_btn(self):
        logger.info("Clicking Save button ...")
        add_sub_save_btn = "/html/body/div[1]/div/div[2]/div/div[2]/div/div[1]/div/form/button"  # TODO use relative xpath
        driver.find_element_by_xpath(add_sub_save_btn).click()
        logger.info("Clicked Save button")
