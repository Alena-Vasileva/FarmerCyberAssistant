# -*- coding: utf-8 -*-
import pyodbc
import json
from os import environ
from dotenv import load_dotenv
from time import time

load_dotenv()


class DataController:    # Tested OK

    TOKEN_RELEVANCE_PERIOD = int(environ['TOKEN_RELEVANCE_PERIOD'])

    with pyodbc.connect(f'Driver={environ["DATABASE_DRIVER"]};Server={environ["DATABASE_SERVER"]};\
            Database={environ["DATABASE_NAME"]};Uid={environ["DATABASE_UID"]};Pwd={environ["DATABASE_PWD"]}')\
            as __connection:
        __cursor = __connection.cursor()

    @staticmethod
    def user_exists(username):
        DataController.__cursor.execute('SELECT username FROM customer WHERE username = ?;', username)
        return DataController.__cursor.fetchone() is not None

    @staticmethod
    def add_user(username, customer_info, pwd_hash):
        DataController.delete_user(username)
        DataController.__cursor.execute('INSERT INTO customer (username, customer_info, pwd_hash)'
                                        'VALUES (?, ?, ?);COMMIT;', username, customer_info, pwd_hash)

    @staticmethod
    def delete_user(username):
        DataController.__cursor.execute('DELETE FROM customer WHERE username = ?;COMMIT;', username)
        DataController.delete_token(username)

    @staticmethod
    def get_customer_info(username):
        DataController.__cursor.execute('SELECT customer_info FROM customer WHERE username = ?;', username)
        data = DataController.__cursor.fetchone()
        return None if data is None else json.loads(data.customer_info)

    @staticmethod
    def update_customer_info(username, new_customer_info):
        DataController.__cursor.execute('UPDATE customer SET customer_info = ?'
                                        'WHERE username = ?; COMMIT;', json.dumps(new_customer_info), username)

    @staticmethod
    def token_exists(token):
        DataController.__cursor.execute(f'SELECT token FROM auth_token WHERE token = ?', token)
        return DataController.__cursor.fetchone() is not None

    @staticmethod
    def add_token(username, token, relevance_period=TOKEN_RELEVANCE_PERIOD):
        DataController.delete_token(username)
        DataController.__cursor.execute('INSERT INTO auth_token (username, token, relevance_limit)'
                                        'VALUES (?, ?, ?);'
                                        'COMMIT;', username, token, round(time()) + relevance_period)

    @staticmethod
    def delete_token(username):
        DataController.__cursor.execute('DELETE FROM auth_token WHERE username = ?; COMMIT;', username)

    @staticmethod
    def get_token(username):
        DataController.__cursor.execute('SELECT token FROM auth_token WHERE username = ?;', username)
        data = DataController.__cursor.fetchone()
        return None if data is None else data.token

    @staticmethod
    def check_token_relevance(token):
        DataController.__cursor.execute('SELECT relevance_limit FROM auth_token WHERE token = ?;', token)
        data = DataController.__cursor.fetchone()
        return data is not None and time() < data.relevance_limit

    @staticmethod
    def get_username_by_token(token):
        DataController.__cursor.execute('SELECT username FROM auth_token WHERE token = ?;', token)
        data = DataController.__cursor.fetchone()
        return None if data is None else data.username

    @staticmethod
    def verify_auth_by_pwd_hash(username, pwd_hash):
        DataController.__cursor.execute(
            'SELECT username FROM customer WHERE username = ? and pwd_hash = ?;', username, pwd_hash)
        return DataController.__cursor.fetchone() is not None

    @staticmethod
    def delete_expired_tokens():    # TODO
        pass
