import json
import logging


def find_open_thread(data, user_id, status="open"):
    if data:
        _threads = {k: v for k, v in data.items() if v["status"] == status and v["user_id"] == user_id}
        if _threads:
            if len(_threads) > 1:
                logging.info("There are more than one open threads. I took the last one.")
            _thread_id = list(_threads.keys())
            _thread_id = _thread_id[len(_threads) - 1]
            return _thread_id
        else:
            return None
    else:
        return None


def create_thread(data, user_id, status="open"):
    _thread_id = "12345678"
    data[_thread_id] = {"user_id": user_id, "status": status}
    with open("bip-1im-support-group.json", "w") as write_file:
        json.dump(data, write_file)
    return _thread_id


if __name__ == '__main__':
    with open("bip-1im-support-group.json", "r") as read_file:
        data = json.load(read_file)

    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        level=logging.INFO
    )

    user_id = "12345678"
    status = "open"

    thread_id = find_open_thread(data, user_id)
    if not thread_id:
        thread_id = create_thread(data, user_id)
    print(thread_id)
