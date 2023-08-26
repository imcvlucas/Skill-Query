import os
import sys
import json
from datetime import datetime

import w3lib.html
import scrapy
from scrapy.spiders import CrawlSpider
from scrapy.linkextractors import LinkExtractor



# set path
FILENAME = __file__
DIRECTORY_PATH = os.path.abspath(os.path.dirname(__file__))
EXPORT_FEED_DIR = os.path.abspath(os.path.join(DIRECTORY_PATH, '../../../export_feed/'))


class DataAnalystSpider(scrapy.Spider):
    """
    Scrape all job links from the given URL and store the data collected in a file.
    """
    name = 'DA_role_spider'
    api_url = 'https://ca.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search?keywords=data+analyst&trk=public_jobs_jobs-search-bar_search-submit&position=1&pageNum'

    custom_settings = {
        'FEEDS': {
            f'{EXPORT_FEED_DIR}/%(name)s/%(time)s.csv': {
                'format': 'csv'
            },
        },
        'DOWNLOAD_DELAY': 0.9,
    }

    def start_requests(self):
        first_job_on_page = 0
        start_url = self.api_url + str(first_job_on_page)
        yield scrapy.Request(url=start_url, callback=self.parse_links, meta={'first_job_on_page': first_job_on_page})
        # self.get_job_details()

    def parse_links(self, response):
        """
        Grab links from each job post.
        """
        first_job_on_page = response.meta['first_job_on_page']
        jobs = response.css('li') # Job postings
        num_jobs_returned = len(jobs)

        job_links = {}
        for job in jobs:
            job_links['link'] = job.css('a::attr(href)').get(default='')
            yield job_links

        ########## Request Next Page ##########
        if num_jobs_returned > 0:
            first_job_on_page = int(first_job_on_page) + 25
            next_url = self.api_url + str(first_job_on_page)
            yield scrapy.Request(url=next_url, callback=self.parse_links, meta={'first_job_on_page': first_job_on_page})


class DAPostSpider(scrapy.Spider):
    """
    Extract data from the scraped links.
    """
    def __init__(self):
        self.name = 'DA_post_spider'
        self.urls = []

    custom_settings = {
        'FEEDS': {
            f'{EXPORT_FEED_DIR}/%(name)s/%(time)s.json': {
                'format': 'json',
            }
        }
    }

    def start_requests(self):
        # get latest extract file
        extract_target_file = self.get_latest_file_extract()
        with open(extract_target_file, 'rt') as f:
            self.urls = [url.strip() for url in f.readlines()]
        # scrape through links
        for url in self.urls[1:]:
            yield scrapy.Request(url=url, callback=self.parse_posts)

    def parse_posts(self, response):
        """
        Extract data from job links.
        """
        seniority_level = response.css('span.description__job-criteria-text::text').get().strip()
        seniority_level_no_tags = w3lib.html.remove_tags(seniority_level)

        employment_level = response.css('span.description__job-criteria-text').get().strip()
        employment_level_no_tage = w3lib.html.remove_tags(employment_level)

        job_description = response.css('div.show-more-less-html__markup').get()
        job_description_no_tags = w3lib.html.remove_tags(job_description)

        yield {
            'role': response.css('h1::text').get().strip(),
            'seniority_level' : seniority_level_no_tags,
            'employment_type' : employment_level_no_tage,
            'job_description' : job_description_no_tags 
        }

    def get_latest_file_extract(self):
        """
        Find the most recent extract in the directory.
        """
        # get current date
        current_date = datetime.date.today()
        swe_export_feed_directory = f'{EXPORT_FEED_DIR}/SWE_role_spider/'
        # find file path of latest extract to scrape
        extract_target_file = ''
        for file in os.listdir(swe_export_feed_directory):
            if (file[:10] == str(current_date)):
                target_file = os.path.join(swe_export_feed_directory, file)
                if os.path.isfile(target_file):
                    extract_target_file = target_file
        return extract_target_file
