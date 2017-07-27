from githubwrapper import GitHubWrapper

token = input("Input, please, token(required): ")
url = input("Input, please, github repository url(required): ")
date_start = input("Input, please, date for start analyze(ex. 01.01.2017)(not required): ")
date_end = input("Input, please, date end(ex. 01.01.2017)(not required): ")
branch = input("Input, please, name branch(default=master)(not required): ")

request = GitHubWrapper(url=url, date_begin=date_start, date_end=date_end, branch=branch, token=token)
request.get_all_stats()

