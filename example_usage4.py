from redfin import RedFin

redfin = RedFin()
redfin.use_proxies = True
redfin.use_browser()
redfin.get_search_results()
redfin.get_property_data()
