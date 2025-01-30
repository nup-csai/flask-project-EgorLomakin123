from .logger_singleton import LoggerSingleton
import sqlite3
from . import passwords_work
from . import sqlite_cursor_singleton
from queue import Queue
from threading import Thread
from functools import wraps
import time

task_queue = Queue()

task_result = Queue()


def task_to_queue(queue):

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            queue.put((func, args, kwargs, task_result))
            res = False
            res = task_result.get()
            return res

        return wrapper

    return decorator


def task_worker(task_queue):
    logger = LoggerSingleton().get_logger()
    while True:
        task, args, kwargs, result_queue = task_queue.get()
        if not (task is None):
            try:
                result = task(*args, **kwargs)
                result_queue.put(result)
            except Exception as e:
                logger.error(e)
            finally:
                task_queue.task_done()


def sql_exception(func):
    logger1 = LoggerSingleton().get_logger()

    @wraps(func)
    def wrapper_func(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except sqlite3.Error as sql_e:
            logger1.error(f"Sqlite error: {sql_e}")
            return -5
        except Exception as e:
            logger1.error(f"Unexpected error: {e}")
            return -5

    return wrapper_func


class DbWork():
    def __init__(self):
        worker_thread = Thread(target=task_worker, args=(task_queue,), daemon=True)
        worker_thread.start()
        self.my_init()
        self.logger1 = LoggerSingleton().get_logger()

    @task_to_queue(task_queue)
    def my_init(self):
        self.db_singleton = sqlite_cursor_singleton.SQLiteCursorSingleton("./app/database.db")
        self.cursor = self.db_singleton.get_cursor()

    '''
    return:
    -1 - wrong password
    -2 - wrong username
    otherwise - user_id
    '''

    @task_to_queue(task_queue)
    @sql_exception
    def check_password(self, user_name, password):
        self.cursor.execute("SELECT id FROM users WHERE user_name = ?", (user_name,))
        user_id = self.cursor.fetchone()
        if user_id is None:
            return -1
        user_id = user_id[0]
        self.cursor.execute("SELECT password FROM users WHERE user_name = ?", (user_name,))
        password_bd = self.cursor.fetchone()
        if passwords_work.verify_password(password, password_bd[0]):
            return user_id
        return -1

    '''
    return:
    -1 - name is already used
    otherwise - user_id
    '''

    @task_to_queue(task_queue)
    @sql_exception
    def register_user(self, user_name, password, contact):
        self.cursor.execute("SELECT id FROM users WHERE user_name = ?", (user_name,))
        user_id = self.cursor.fetchone()
        if user_id is None:
            self.cursor.execute("INSERT INTO users (user_name, password, contact, avatar_id) VALUES (?, ?, ?, 1)",
                                (user_name,
                                 passwords_work.hash_password(password),
                                 contact,))
            self.db_singleton.commit()
            new_user_id = self.cursor.lastrowid
            return new_user_id
        return -1

    '''
    return:
    {lot_id:
     {"author_id": author_id,
      "description": description,
       "category": category,
        "weight": weight,
         "images" : {0: "path", ...}
     }, ...
    }
    '''

    @task_to_queue(task_queue)
    @sql_exception
    def get_lots(self, user_id=-1):
        if user_id == -1:
            self.cursor.execute(
                "SELECT lots.id, lots.author_id, lots.description, categories.name, lots.weight FROM lots "
                "LEFT JOIN categories ON lots.category = categories.id "
                "WHERE lots.active = 1")
        else:
            self.cursor.execute(
                "SELECT lots.id, lots.author_id, lots.description, categories.name, lots.weight FROM lots "
                "LEFT JOIN categories ON lots.category = categories.id "
                "WHERE lots.active = 1 AND lots.author_id = ?", (user_id,))
        lots = [i for i in self.cursor.fetchall()]
        answer = {}
        self.logger1.debug(f"lots: {lots}")
        for lot in lots:

            to_add = {"id": lot[0],
                      "author_id": lot[1],
                      "description": lot[2],
                      "category": lot[3],
                      "weight": lot[4],
                      "images": {}}
            self.cursor.execute("SELECT images.path "
                                "FROM images "
                                "LEFT JOIN img_to_lot ON images.id = img_to_lot.img_id "
                                "LEFT JOIN lots ON img_to_lot.lot_id = lots.id "
                                "WHERE lots.id = ?", (lot[0],))
            self.logger1.debug(f"lot: {lot[4]}")
            img_paths = self.cursor.fetchall()
            self.logger1.debug(f"img_paths: {img_paths}")
            count = 0
            for path in img_paths:
                to_add["images"][count] = path[0]
                count += 1
            answer[lot[0]] = to_add
        return answer

    '''
    return:
    {"author_id": author_id,
     "description": description,
     "category": categories.name,
     "weight": weight,
     "images" : {0: "path", ...}
    '''

    @task_to_queue(task_queue)
    @sql_exception
    def get_lot(self, lot_id):
        self.cursor.execute(
            "SELECT lots.author_id, lots.description, categories.name, lots.weight FROM lots "
            "LEFT JOIN categories ON lots.category = categories.id "
            "WHERE lots.active = 1 AND lots.id = ?", (lot_id,))
        lot = self.cursor.fetchone()
        answer = {"author_id": lot[0], "description": lot[1], "category": lot[2], "weight": lot[3], "images": {}}
        self.cursor.execute("SELECT images.path FROM img_to_lot"
                            " LEFT JOIN images ON img_to_lot.img_id = images.id"
                            " WHERE img_to_lot.id = ?", (lot_id,))
        img_paths = self.cursor.fetchall()
        count = 0
        for path in img_paths:
            answer["images"][count] = path[0]
            count += 1
        return answer

    '''
    return:
    {"id": users.id,
     "name": users.user_name,
     "contact": users.contact,
     "avatar": images.path
     }
    '''

    @task_to_queue(task_queue)
    @sql_exception
    def get_user(self, user_id):
        self.cursor.execute(
            "SELECT users.id, users.user_name, users.contact, images.path FROM users"
            " LEFT JOIN images ON users.avatar_id = images.id "
            " WHERE users.id = ?", (user_id,))
        user = self.cursor.fetchone()
        answer = {"id": user[0], "name": user[1], "contact": user[2], "avatar": user[3]}
        return answer

    @task_to_queue(task_queue)
    @sql_exception
    def add_lot_by_user(self, author_id, description, category, weight):
        self.logger1.debug(f"add_lot_by_user: {author_id}, {description}, {category}, {weight}")
        self.cursor.execute("INSERT INTO lots (author_id, description, category, weight, active)"
                            "VALUES (?, ?, ?, ?, ?)", (author_id, description, category, weight, 1,))
        self.db_singleton.commit()
        return self.cursor.lastrowid

    @task_to_queue(task_queue)
    @sql_exception
    def add_img_to_lot(self, lot_id, img_path):
        self.cursor.execute("INSERT INTO images (path) VALUES (?)", (img_path,))
        self.db_singleton.commit()
        img_id = self.cursor.lastrowid
        self.cursor.execute("INSERT INTO img_to_lot (lot_id, img_id) VALUES (?, ?)", (lot_id, img_id,))
        self.db_singleton.commit()

    @task_to_queue(task_queue)
    @sql_exception
    def add_avatar(self, user_id, img_path):
        self.cursor.execute(f"INSERT INTO images (path) VALUES ('{img_path}')")
        self.db_singleton.commit()
        img_id = self.cursor.lastrowid
        self.logger1.debug(f"Adding image {img_path} img_id: {img_id}, user_id: {user_id}")
        self.cursor.execute("UPDATE users SET avatar_id = ? WHERE id = ?", (img_id, user_id,))
        self.db_singleton.commit()

    @task_to_queue(task_queue)
    @sql_exception
    def disable_lot(self, lot_id):
        self.cursor.execute("UPDATE lots SET active = 0 WHERE id = ?", (lot_id,))
        self.db_singleton.commit()

    @task_to_queue(task_queue)
    @sql_exception
    def give_img_last_id(self):
        self.cursor.execute("SELECT COUNT(*) FROM images")
        answer = self.cursor.fetchone()
        return answer[0]

    @task_to_queue(task_queue)
    @sql_exception
    def get_category(self, category_id):
        self.cursor.execute("SELECT categories.name FROM categories WHERE id = ?", (category_id,))
        answer = self.cursor.fetchone()
        return answer[0]
