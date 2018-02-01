from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.keys import Keys
import re
import time
import csv
#import house_info as hi

class house:
    def __init__(self, url):
        self.url = url
        self.zPrefix = 'https://www.zillow.com'
        self.zSuffix = '?fullpage=true'
        self.zestimateVal = None
        self.zestimateLB = None
        self.zestimateUB = None
        self.zestimateRent = None
        self.taxLastYear = None
        self.nbeds = None
        self.nbath = None
        self.unitSize = None
        self.listPrice = None
        self.isAuction = None
        self.zpr = None


    def getInfo(self):
        driver = webdriver.Chrome()
        time.sleep(1)
        driver.get(self.zPrefix+self.url+self.zSuffix)
        time.sleep(.2)
        # get zestimate value
        try:
            zestimateValStr = driver.find_element_by_class_name('zestimate-value').get_property('innerText')
            self.zestimateVal = float(zestimateValStr[1:].replace(',', ''))
        except NoSuchElementException:
            self.zestimateVal = None

        # get upper and lower bound of zestimate value
        try:
            zestimateSecondaryStr = driver.find_element_by_class_name('secondary-zestimate-items').get_property('innerText')
            zestimateRangeStr = re.findall('[,\d]+', zestimateSecondaryStr)
            self.zestimateLB = float(zestimateRangeStr[0].replace(',', ''))
            self.zestimateUB = float(zestimateRangeStr[1].replace(',', ''))
        except NoSuchElementException:
            self.zestimateLB = None
            self.zestimateUB = None

        # get zestimate rent
        try:
            zestimateRentStr = driver.find_element_by_class_name('tertiary-zestimate-items').get_property('innerText')
            zestimateRentStr2 = re.findall('[,\d]+', zestimateRentStr)
            self.zestimateRent = float(zestimateRentStr2[0].replace(',', ''))
        except (NoSuchElementException, IndexError):
            self.zestimateRent = None

            # get tax info
        try:
            taxInfoStr = driver.find_element_by_id('hdp-tax-history').get_property('innerText')
            taxLastYearStr = re.findall('[,\d]+', taxInfoStr)
            self.taxLastYear = float(taxLastYearStr[1].replace(',', ''))
        except NoSuchElementException:
            self.taxLastYear = None

        # get number of beds, bath and unit size
        bbsizeStr = driver.find_element_by_class_name('zsg-content-header').get_property('innerText')
        bbsizeStr2 = re.findall('[\d.,-]+', bbsizeStr.split('\n')[2])
        try:
            self.nbeds = float(bbsizeStr2[0].replace(',', ''))
        except:
            self.nbeds = None

        try:
            self.nbath = float(bbsizeStr2[1].replace(',', ''))
        except:
            self.nbath = None
        try:
            self.unitSize = float(bbsizeStr2[2].replace(',', ''))
        except:
            # if the string before sqft cannot transform into number, probably it is '--', which means the unit size is unknown
            self.unitSize = None

        # get list price of this unit
        listPriceStr = driver.find_element_by_class_name('zsg-lg-1-3').get_property('innerText')
        self.isAuction = False
        try:
            self.listPrice = float(listPriceStr.split('\n')[1][1:].replace(',', ''))
        except ValueError:
            self.listPrice = None
            self.isAuction = True

        driver.close()
        return True

    def get_zpr(self):
        if not self.listPrice or not self.zestimateRent or not self.taxLastYear:
            self.zpr = None
            return False
        else:
            self.zpr = self.compute_zpr(1.0)
            return True

    def compute_zpr(self, discount):
        return self.listPrice*discount/(self.zestimateRent*12-self.taxLastYear)

def findNextButton(driver):
    try:
        nextButton = driver.find_element_by_class_name('zsg-pagination-next')
        return nextButton
    except NoSuchElementException:
        return None

def findAllHouseThisPage(driver):
    urls = re.findall('/homedetails/\S+zpid/', driver.page_source)
    return urls

def findAllHouseUrl(driver):
    nextButton = findNextButton(driver)
    house_url = []
    iPage = 0
    maxPage = 10
    print('Abstracting House URL from Zillow...')
    while nextButton:
        iPage += 1
        if iPage>maxPage:
            break
        print 'page: ', iPage
        url_house_this_page = findAllHouseThisPage(driver)
        house_url += url_house_this_page
        #Click next button
        nextButton.click()
        time.sleep(5)
        nextButton = findNextButton(driver)
    print('Complete!')
    return house_url

def unitTest(url):
    curHouse = house(url)
    curHouse.getInfo()
    isZprAvailable = curHouse.get_zpr()
    return curHouse

#cur_url = '/homedetails/5-Arcadia-Ln-Hicksville-NY-11801/31285054_zpid/'
#curHouse = unitTest(cur_url)
#print cur_url, curHouse.zpr, curHouse.nbeds, ' beds ', curHouse.nbath, ' bath'
#exit()

outputCsvFileName = 'data/11801/'
driver = webdriver.Chrome()
driver.get("https://www.zillow.com/")
searchBox = driver.find_element_by_name('citystatezip')
searchBox.clear()
searchBox.send_keys('11801')
searchBox.send_keys(Keys.RETURN)
filterMenu = driver.find_element_by_class_name('filter-menu')
filterMenu.click()
time.sleep(1)
potentialListingCheckBox = driver.find_elements_by_class_name('listing-category')
potentialListingCheckBox[1].click()
time.sleep(5)


urls=findAllHouseUrl(driver)
driver.close()
houseList = []
for url in urls:
    curHouse = house(url)
    repeatCounter = 0
    repeatMax = 5
    isRepeat = True
    while isRepeat:
        try:
            curHouse.getInfo()
            isZprAvailable = curHouse.get_zpr()
            isRepeat = False
        except:
            repeatCounter+=1
            isRepeat = repeatCounter<repeatMax

    if not curHouse.get_zpr():
        print url,'zpr unavailable', curHouse.nbeds, ' beds ', curHouse.nbath, ' bath'
    else:
        print url, curHouse.zpr, curHouse.nbeds, ' beds ', curHouse.nbath, ' bath'

    houseList.append(curHouse)

for curHouse in houseList:
