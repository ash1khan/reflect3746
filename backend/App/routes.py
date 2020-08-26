#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
__author__ = "Ashiquzzaman Khan"
__version__ = "0.0.1"
__email__ = "dreadlordn@gmail.com"
__status__ = "Production"
__license__ = "GPL-3"
__copyright__ = "Copyright 2020, PandorAstrum"
__date__ = 8/25/2020
__desc__ = "API routes"
"""
import json
import time
from datetime import datetime

from flask import redirect, url_for

import crochet
import json

from flask import Blueprint, jsonify, make_response, request
from bson.json_util import dumps, loads
from scrapy import spiderloader
from scrapy.crawler import CrawlerRunner
from scrapy.utils.project import get_project_settings

from App import db
from scraper.scraper import Scraper

crochet.setup()                                             # initialize crochet
urls_list = []                                              # temp store urls
domain = ""
scrape_in_progress = False                                  # progress flag
scrape_complete = False                                     # complete flag
_selected_spider = None                                     # Selected Spider
_scraper = Scraper()
_crawl_runner = CrawlerRunner(_scraper.get_settings())    # requires the Twisted reactor to run

api = Blueprint('api', __name__, template_folder='templates')   # Blueprints

# END POINTS ====================================================================================
@api.route('/server_status', methods=["GET"])
def server_status():
    """Ping Server to check if it is running"""
    return jsonify({'host': request.host, 'status': 200})


@api.route('/database_status', methods=["GET"])
def database_status():
    """Check if database table exist and connection established"""
    db.mongoatlas.connect()
    if db.mongoatlas.client is not None:
        db.mongoatlas.connect_db()
        db_name = db.mongoatlas.db_name
        username = db.mongoatlas.username
        nodes = db.mongoatlas.node_list[0]
        return jsonify({
            "database": db_name,
            "nodes": nodes,
            "username": username
        })
    else:

        error_message = db.mongoatlas.error
        return jsonify({
            "error": error_message
        })


@api.route('/spider', methods=["GET", "POST"])
def spider():
    """Query Spider or Create one"""
    if request.method == "POST":
        """Create a spider via query string parameters."""
        # get name and parameter from FORM
        # db collection add
        return
    if db.mongoatlas.client is not None:
        _spiders_col = loads(dumps(db.spider_col.find()))
        return db.json_encoder.encode(_spiders_col)
    return jsonify({"error": "Not Connected"})


@api.route('/run', methods=["POST"])
def spider_run():
    """start crawling"""
    global domain
    global _selected_spider
    if request.method == "POST":
        params = request.get_json() # get form
        spider_kwargs = params["spider_kwargs"]
        _selected_spider = spider_kwargs['spider_name']
        spider_settings = params["spider_settings"]
        domain = spider_kwargs['baseurl'].split("//")[-1].split("/")[0].split('?')[0]
        if db.scraped_col.count_documents({'name': domain}, limit=1) != 0:   # if already exist
            pass # pull data and return jsonify
            return url_for('get_results_of', _id='_id')
        else:
            global scrape_in_progress
            global scrape_complete
            if not scrape_in_progress:
                scrape_in_progress = True
                # build params for spider
                _spider_kwargs = {
                    "base_url": spider_kwargs['baseurl'],
                    'domain': domain,
                    "spider_settings": {
                        "LOG_LEVEL": "INFO",
                        "DOWNLOAD_DELAY": spider_settings["delay"],
                        "RANDOMIZE_DOWNLOAD_DELAY": True
                    }
                }

                scrape_with_crochet(_spider=_scraper.get_spider(_selected_spider),
                                    _kwargs=_spider_kwargs,
                                    _list_output=urls_list)                  # run spider
                return jsonify({"Status": 200, "msg": "Scraping started"})
            elif scrape_complete:
                return jsonify({"Status": 200, "msg": "Scraping Completed"})
            return jsonify({"Status": 102, "msg": "Scraping in Progress"})


@api.route('/results', methods=["GET"])
def get_results():
    """
    Get the results only if a spider has results
    """
    global scrape_complete
    if scrape_complete:
        return json.dumps(urls_list)
    return 'Scrape Still Progress'


@api.route('/logs', methods=["GET"])
def get_logs():
    """
    Get history of scraping from database
    """
    return 'logs'


@api.route('/results/<_id>', methods=["GET"])
def get_results_of(_id):
    """
    Get a single results
    """
    return 'get single results'


# NECESSARY METHODS TO CALL =====================================================================
@crochet.run_in_reactor
def scrape_with_crochet(_spider, _kwargs, _list_output):
    global _crawl_runner
    eventual = _crawl_runner.crawl(_spider, kwargs=_kwargs, urls_list=_list_output)
    eventual.addCallback(finished_scrape)


def finished_scrape(null):
    """
    A callback that is fired after the scrape has completed.
    Set a flag to allow display the results from /results
    """
    global scrape_complete
    global scrape_in_progress
    global urls_list
    global domain
    global _selected_spider
    scrape_complete = True
    scrape_in_progress = False

    _urls = {k: [d.get(k) for d in urls_list] for k in set().union(*urls_list)}
    _u = []
    for u in urls_list:
        v = u["urls"]

    print(_urls)
    #build data to dump
    scraped = {
        "domain": domain,
        "urls": _urls,
    }
    logs = {
        "spidername": _selected_spider,
        'timestamp': datetime.utcnow()
    }

    # dump to mongo db

    # call url route to results


