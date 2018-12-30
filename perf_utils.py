
class PerfResult(object):
    def __init__(self, name, value, base_name=None):
        self.name = name
        self.value = value
        self.base_name = base_name

    def to_json(self):
        return {
            'name': self.name,
            'value': self.value,
            'base_name': self.base_name
        }

    @staticmethod
    def from_json(json):
        return PerfResult(json['name'], json['value'], json['base_name'])

class PerfResults(object):
    def __init__(self):
        self.names = []
        self.results = {}

    def add_result(self, result):
        if result.name in self.names:
            raise Exception('Duplicate result name {}'.format(name))
        self.names.append(result.name)
        self.results[result.name] = result

    def add(self, name, result, base_name=None):
        self.add_result(PerfResult(name, result, base_name))

    def get_results_str(self):
        max_name_len = max(len(name) for name in self.names)

        lines = []
        for name in self.names:
            result = self.results[name]

            if result.base_name is not None:
                base_result = self.results[result.base_name]
                line = '{0}: {1:.2f}us ({2:.2f}us without overhead evaluated in {3})'.format(
                    name.ljust(max_name_len), result.value,
                    result.value - base_result.value, result.base_name)
            else:
                line = '{0}: {1:.2f}us'.format(
                    name.ljust(max_name_len), result.value)

            lines.append(line)

        return '\n'.join(lines)

    def to_json(self):
        return [self.results[name].to_json()
                for name in self.names]

    @staticmethod
    def from_json(json):
        ret = PerfResults()
        for json_result in json:
            ret.add_result(PerfResult.from_json(json_result))
        return ret
