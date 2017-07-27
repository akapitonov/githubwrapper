import json
from request import Request
from datetime import datetime


class GitHubWrapper:
    BASE_URL = "https://api.github.com/"
    COUNT_RESULTS = 30
    COUNT_RESULTS_ON_PAGE = 100
    ISSUES_OLD_DELTA = 14
    PULL_REQUEST_OLD_DELTA = 30
    DEFAULT_BRANCH = 'master'

    def __init__(self, url, date_begin=None, date_end=None, branch=DEFAULT_BRANCH, token=None):
        self.repo = self.get_short_url(url)
        self.date_begin = self.str_to_date(date_begin)
        self.date_end = self.str_to_date(date_end)
        self.branch = branch if branch else self.DEFAULT_BRANCH
        self.token = token
        self._check_token()

    @property
    def repo_url(self):
        return "repos/%s/" % self.repo if self.repo else None

    def _check_token(self):
        if self.token is None or len(self.token) < 2:
            raise Exception('Error. Token is not be empty')

    @staticmethod
    def get_short_url(url):
        short_url = None
        if url and url.find('/') > 0:
            words = url.split('/')
            short_url = "%s/%s" % (words[3], words[4]) if len(words) > 3 else None
        if short_url is None:
            raise Exception('Error. Wrong repository url')
        return short_url

    @staticmethod
    def str_to_date(str_date):
        result = None
        if str_date:
            try:
                result = datetime.strptime(str_date, '%d.%m.%Y')
            except ValueError:
                print('Wrong date format. ex. 2017.06.02')
                raise
        return result

    def _is_default_branch(self):
        return self.branch == self.DEFAULT_BRANCH

    def _send_request(self, url):
        if url:
            url = "%s%s" % (self.BASE_URL, url)
            if self.token:
                url = "%s&access_token=%s" % (url, self.token)
            r = Request(url)
            response = r.send()
            return response
        return None

    def _get_users_commits_default_branch(self):
        """
        Количество коммитов у пользователей в ветке мастер без фильтрации по датам
        Эту информацию можно получить у github API за 1 запрос
        :return: словарь пользователь:количество коммитов
        """
        url_request = "%scontributors?page=1" % self.repo_url
        items = self._send_request(url_request)[:self.COUNT_RESULTS]
        contributors = {}
        for item in items:
            login = item.get('login', 'Unknown')
            contributions = item.get('contributions', 0)
            if login in contributors:
                contributors[login] += contributions
            else:
                contributors[login] = contributions
        return contributors

    def _sort_and_print_commits(self, d):
        """
        Сортировка и вывод пользователей с коммитами
        :param d: словарь с пользователями и коммитами
        :return:
        """
        if d and type(d) == dict:
            commits = sorted(d.items(), key=lambda key: key[1], reverse=True)[:self.COUNT_RESULTS]
            for commit in commits:
                print(commit[0], commit[1])

    def _get_users_commits(self):
        """
        Количество коммитов у пользователей в указанной ветке и в указанном временном диапазоне
        с помощью перебора по всем коммитам если нужна фильтрация
        :return: словарь пользователь:количество коммитов
        """
        query_origin = "%scommits?" % self.repo_url
        
        if self.date_begin and self.date_end is None:
            query_origin += "since=%s" % self.date_begin.isoformat()
        elif self.date_end and self.date_begin is None:
            query_origin += "until=%s" % self.date_end.isoformat()
        elif self.date_begin and self.date_end:
            query_origin += "since=%s&until=%s" % (self.date_begin.isoformat(), self.date_end.isoformat())

        query_origin += "&sha=%s&" % self.branch

        commits = {}
        page = 1
        while True:
            query = "%spage=%d&per_page=%d" % (query_origin, page, self.COUNT_RESULTS_ON_PAGE)
            results = self._send_request(query)

            if results:
                for item in results:
                    committer = item.get('author', None)
                    if committer:
                        committer_login = committer.get('login', None)
                        if committer_login in commits:
                            commits[committer_login] += 1
                        else:
                            commits[committer_login] = 1

                page += 1
            else:
                break

        return commits

    def _get_issues(self, state='open', type_query='issue'):
        """
        Метод позволяет через раздел search/issue github api получить информацию о количестве по открытым и закрытым
        issues и открытым pull-requests, к сожалению для закрытых pull-requests выводит неверную информацию
        :param state: открытые или закрытые issueus/pull-requests
        :param type_query: issueus/pull-requests
        :return: количество issues/pull-requests
        """
        date_begin = self.date_begin.strftime("%Y-%m-%d") if self.date_begin else None
        date_end = self.date_end.strftime("%Y-%m-%d") if self.date_end else None
        par_query_date = 'created' if state == 'open' else 'closed'

        query = "search/issues?q=repo:%s+type:%s+is:%s" % (self.repo, type_query, state)
        if type_query == 'pr' and not self._is_default_branch():
            query += "+base:%s" % self.branch

        if date_begin and date_end is None:
            query += "+%s:>=%s" % (par_query_date, date_begin)
        elif date_begin is None and date_end:
            query += "+%s:<=%s" % (par_query_date, date_end)
        elif date_begin and date_end:
            query += "+%s:%s..%s" % (par_query_date, date_begin, date_end)

        results = self._send_request(query)
        return results.get('total_count', 0)

    def _get_closed_pull_requests(self):
        """
        Количество закрытых pull-requests с фильтрацией по ветке и датам
        :return: количество
        """
        state = 'closed'
        page = 1
        count = 0
        query_origin = "%spulls?per_page=%d&state=%s" % (self.repo_url, self.COUNT_RESULTS_ON_PAGE, state)
        if not self._is_default_branch():
            query_origin += "&base=%s" % self.branch

        while True:
            query = "%s&page=%d" % (query_origin, page)
            results = self._send_request(query)

            if results:
                if self.date_begin or self.date_end:
                    for item in results:
                        closed_at = item.get('closed_at', None)
                        closed_at = datetime.strptime(closed_at, '%Y-%m-%dT%H:%M:%SZ')
                        if (self.date_begin and self.date_end is None and closed_at >= self.date_begin) or \
                                (self.date_begin is None and self.date_end and closed_at <= self.date_end) or \
                                (self.date_begin and self.date_end and self.date_begin <= closed_at <= self.date_end):
                            count += 1
                else:
                    count += len(results)

                page += 1
            else:
                break
        return count

    def _get_old_prs_or_issues(self, type_query='pulls', delta=PULL_REQUEST_OLD_DELTA):
        """
        Количество старых issues или pull-requests.
        Поиск выполняется среди открытых и закрытых issues\pull-requests.
        Old issue - это issue не закрытая за 13 дней
        Old pull-request - это pull-request не закрытый за 29 дней
        :param type_query:
        :param delta:
        :return:
        """
        count = 0
        page = 1
        query_origin = "%s%s?state=all&per_page=%d" % (self.repo_url, type_query, self.COUNT_RESULTS_ON_PAGE)

        if type_query == 'pulls' and not self._is_default_branch():
            query_origin += "&base=%s" % self.branch

        while True:
            query = "%s&page=%d" % (query_origin, page)
            results = self._send_request(query)
            if results:
                for item in results:
                    created_at = item.get('created_at', None)
                    created_at = datetime.strptime(created_at, '%Y-%m-%dT%H:%M:%SZ')
                    if (self.date_begin and self.date_end is None and created_at >= self.date_begin) or \
                            (self.date_begin is None and self.date_end and created_at <= self.date_end) or \
                            (self.date_begin and self.date_end and self.date_begin <= created_at <= self.date_end) or \
                            (self.date_begin is None and self.date_end is None):
                        closed_at = item.get('closed_at', None)
                        closed_at = datetime.strptime(closed_at, '%Y-%m-%dT%H:%M:%SZ') if closed_at else datetime.now()
                        delta_dates = closed_at - created_at
                        if delta_dates.days >= delta:
                            count += 1
                page += 1
            else:
                break

        return count

    def get_users_commits(self):
        print('Group user by commits:')
        if self._is_default_branch() and self.date_begin is None and self.date_end is None:
            commits = self._get_users_commits_default_branch()
        else:
            commits = self._get_users_commits()

        self._sort_and_print_commits(commits)

    def get_open_issues(self):
        print('Count opened issues:', self._get_issues('open'))

    def get_closed_issues(self):
        print('Count closed issues:', self._get_issues('closed'))

    def get_open_pull_requests(self):
        print('Count opened pull-requests:', self._get_issues('open', 'pr'))

    def get_closed_pull_requests(self):
        print('Count closed pull-requests:', self._get_closed_pull_requests())

    def get_old_issues(self):
        print('Count "old" issues:', self._get_old_prs_or_issues('issues', self.ISSUES_OLD_DELTA))

    def get_old_requests(self):
        print('Count "old" requests:', self._get_old_prs_or_issues('pulls', self.PULL_REQUEST_OLD_DELTA))

    def get_all_stats(self):
        self.get_users_commits()
        self.get_open_issues()
        self.get_closed_issues()
        self.get_open_pull_requests()
        self.get_closed_pull_requests()
        self.get_old_issues()
        self.get_old_requests()
