# coding=utf-8

import sys

reload(sys)
sys.setdefaultencoding('utf-8')

from selenium.webdriver import Firefox
from time import sleep
import requests
from bs4 import BeautifulSoup
from collections import OrderedDict
import re
from sets import Set
import json
from random import choice, randint
from selenium.webdriver import Firefox
from selenium.webdriver.firefox.webdriver import FirefoxProfile

from requests.packages.urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

reg_property_history_row = re.compile('propertyHistory\-[0-9]+')
reg_property_urls = re.compile('(/[A-Z][A-Z]/[A-Za-z\-/0-9]+/home/[0-9]+)')
user_agent_header = {
    'User-agent': 'Mozilla/5.0 (Windows NT 6.3; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/49.0.2623.112 Safari/537.36'}


class RedFin():
    def __init__(self):
        self.start_url = 'https://www.redfin.com/city/517/CA/Anaheim/'
        self.session = requests.Session()
        self.use_selenium = False
        #  proxy option can be set after class object is loaded
        self.use_proxies = False
        self.output_data = []
        self.property_urls = []
        #  load proxies from file one per line proxy:port format
        self.proxies = [l.rstrip() for l in open('proxies.txt').readlines()]
        #  make a separate session for each proxy
        self.sessions = {}
        for proxy in self.proxies:
            self.sessions[proxy] = {
                'session': requests.Session(),
                'proxy': {'http': 'http://' + proxy,
                          'https': 'https://' + proxy}
            }
        # load data collected so far in order to avoid needing to scrape
        #  the same data twice
        try:
            self.output_data = json.loads(open('redfin_output.json').read())
        except:
            self.output_data = []

    def rand_sleep(self):
        #  you can set the random sleep time for no browser mode here
        sleep(randint(5, 10))

    def parse_finished_urls(self):
        #  function for removing urls that have already completed
        done_urls_list = Set()
        for property_data in self.output_data:
            url = property_data['url'][22:]
            done_urls_list.add(url)
            if url in self.property_urls: self.property_urls.remove(url)
        print(str(len(done_urls_list)) + ' properties already done')
        print(str(len(self.property_urls)) + ' proeprties to go')

    def get_search_results(self):
        page_source = self.request_search_page(self.start_url)
        self.property_urls = reg_property_urls.findall(page_source.replace('\\u002F', '/'))
        self.property_urls = list(Set(self.property_urls))
        print('found ' + str(len(self.property_urls)) + ' results')
        self.parse_finished_urls()

    def request_search_page(self, page_url):
        if self.use_selenium:
            return self.get_page_selenium(page_url)
        else:
            return self.make_page_request(page_url)

    def get_property_data(self):
        count = 0
        for property_url in self.property_urls:
            self.output_data.append(self.get_property_page(property_url))
            count += 1
            print('finished page ' + str(count))
            open('redfin_output.json', 'w').write(json.dumps(self.output_data, indent=4))

    def make_page_request(self, property_url):
        self.rand_sleep()
        if self.use_selenium:
            return self.get_page_selenium('https://www.redfin.com' + property_url)
        elif self.use_proxies:
            return self.make_page_request_proxy(property_url)
        else:
            return self.make_page_request_no_proxy(property_url)

    def make_page_request_no_proxy(self, property_url):
        #  use a loop to handle various http request errors and retry
        #  if 10 fails reached assume we've been blcoked
        for i in range(10):
            try:
                http_response = self.session.get(property_url, headers=user_agent_header, verify=False)
                if http_response.status_code == 200: break
            except Exception as e:
                print(1, 'Request error')
            if i == 9: print(1, 'blocked error');exit()
        return http_response.text

    def make_page_request_proxy(self, property_url):
        #  use a loop to handle various http request errors and retry
        #  if 10 fails reached assume we've been blcoked
        for i in range(10):
            try:
                session = self.sessions[choice(self.proxies)]
                http_response = session['session'].get(property_url, headers=user_agent_header,
                                                       proxies=session['proxy'], verify=False)
                if http_response.status_code == 200: break
            except Exception as e:
                print(2, 'Request error')
            if i == 9: print(2, 'blocked error');exit()
        return http_response.text

    def get_property_page(self, property_url):
        page_source = self.make_page_request(property_url)
        return self.parse_property_page(page_source, property_url)

    def parse_property_page(self, page_source, property_url):
        self.soup = BeautifulSoup(page_source, 'html.parser')
        property_data = OrderedDict()

        #  use try catch to handle when a data point is not available
        try:
            property_data['street_address'] = self.soup.find('span', attrs={'itemprop': 'streetAddress'}).get_text()
        except:
            property_data['street_address'] = 'N/A';print('street_address not found')
        try:
            property_data['address_locality'] = self.soup.find('span', attrs={'itemprop': 'addressLocality'}).get_text()
        except:
            property_data['address_locality'] = 'N/A';print('address_locality not found')
        try:
            property_data['address_region'] = self.soup.find('span', attrs={'itemprop': 'addressRegion'}).get_text()
        except:
            property_data['address_region'] = 'N/A';print('address_region not found')
        try:
            property_data['postal_code'] = self.soup.find('span', attrs={'itemprop': 'postalCode'}).get_text()
        except:
            property_data['postal_code'] = 'N/A';print('postal_code not found')
        try:
            property_data['price'] = self.soup.find('div', attrs={'class': 'info-block price'}).find('div').get_text()
        except:
            property_data['price'] = 'N/A';print('price not found')
        try:
            property_data['beds'] = self.soup.find('div', attrs={'data-rf-test-id': 'abp-beds'}).find('div').get_text()
        except:
            property_data['beds'] = 'N/A';print('beds not found')
        try:
            property_data['baths'] = self.soup.find('div', attrs={'data-rf-test-id': 'abp-baths'}).find(
                'div').get_text()
        except:
            property_data['baths'] = 'N/A';print('baths not found')
        try:
            property_data['sqFt'] = self.soup.find('div', attrs={'data-rf-test-id': 'abp-sqFt'}).find('span', attrs={
                'class': 'main-font statsValue'}).get_text()
        except:
            property_data['sqFt'] = 'N/A';print('sqFt not found')
        try:
            property_data['price_per_sqFt'] = self.soup.find('div', attrs={'data-rf-test-id': 'abp-sqFt'}).find('div',
                                                                                                                attrs={
                                                                                                                    "data-rf-test-id": "abp-priceperft"}).get_text()
        except:
            property_data['price_per_sqFt'] = 'N/A';print('price_per_sqFt not found')
        try:
            property_data['year_built'] = self.soup.find('span', attrs={"data-rf-test-id": "abp-yearBuilt"}).find(
                'span', attrs={'class': 'value'}).get_text()
        except:
            property_data['year_built'] = 'N/A';print('year_built not found')
        try:
            property_data['days_on_redfin'] = self.soup.find('span',
                                                             attrs={"data-rf-test-id": "abp-daysOnRedfin"}).find('span',
                                                                                                                 attrs={
                                                                                                                     'class': 'value'}).get_text()
        except:
            property_data['days_on_redfin'] = 'N/A';print('days_on_redfin not found')
        try:
            property_data['status'] = self.soup.find('span', attrs={"data-rf-test-id": "abp-status"}).find('span',
                                                                                                           attrs={
                                                                                                               'class': 'value'}).get_text()
        except:
            property_data['status'] = 'N/A';print('status not found')

        property_data['summary'] = self.soup.find('div', attrs={'class': 'remarks'}).get_text()
        for row in self.soup.find('div', attrs={'class': 'more-info-div'}).find_all('tr'):
            cells = row.find_all('td')
            property_data[cells[0].get_text().strip()] = cells[1].get_text().strip()

        # use loops to maintain data structure ina dict
        property_data['property_details'] = OrderedDict()
        for category in self.soup.find('div', attrs={'class': 'amenities-container'}).children:
            key = category.contents[0].get_text().strip()
            property_data['property_details'][key] = OrderedDict()
            for row in category.contents[1].find_all('div', attrs={'class': 'amenity-group'}):
                key2 = row.find('h4').get_text()
                property_data['property_details'][key][key2] = []
                for row2 in row.find_all('li'):
                    property_data['property_details'][key][key2].append(row2.get_text())

        property_data['propert_history'] = []
        for row in self.soup.find_all('tr', attrs={'id': reg_property_history_row}):
            data_cells = row.find_all('td')
            history_data_row = OrderedDict()
            history_data_row['date'] = data_cells[0].get_text()
            history_data_row['event & source'] = data_cells[1].get_text()
            history_data_row['price'] = data_cells[2].get_text()
            history_data_row['appreciation'] = data_cells[3].get_text()
            property_data['propert_history'].append(history_data_row)

        property_data['url'] = 'https://www.redfin.com' + property_url
        self.output_data.append(property_data)
        return property_data

    def use_browser(self):
        self.use_selenium = True
        firefox_profile = FirefoxProfile()
        #  might as well turn off images since we don't need them
        if self.use_proxies:
            #  if use proxies is true load firefox with proxies
            firefox_profile.set_preference("permissions.default.image", 2)
            proxy_host, proxy_port = choice(self.proxies).split(':')
            firefox_profile.set_preference("network.proxy.type", 1)
            firefox_profile.set_preference("network.proxy.http", proxy_host)
            firefox_profile.set_preference("network.proxy.http_port", int(proxy_port))
            firefox_profile.set_preference("network.proxy.ssl", proxy_host)
            firefox_profile.set_preference("network.proxy.ssl_port", int(proxy_port))
        self.driver = Firefox(firefox_profile)
        self.driver.implicitly_wait(2)

    def get_page_selenium(self, page_url):
        self.driver.get(page_url)
        self.selenium_bypass_captcha()
        return self.driver.page_source

    def selenium_bypass_captcha(self):
        #  basic code for handling captcha
        #  this requires the user to actually solve the captcha and then continue
        try:
            self.driver.switch_to_frame(self.driver.find_element_by_xpath('//iframe[@title="recaptcha widget"]'))
            self.driver.find_element_by_class_name('recaptcha-checkbox-checkmark').click()
            print('solve captcha ( pop up only ) and press enter to continue')
            raw_input()
            self.driver.switch_to_default_content()
            self.driver.find_element_by_id('submit').click()
        except Exception as e:
            pass
