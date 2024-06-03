import orjson as json


def load_json(filename):
    with open(filename, 'r', encoding='utf-8') as file:
        return json.loads(file.read())
