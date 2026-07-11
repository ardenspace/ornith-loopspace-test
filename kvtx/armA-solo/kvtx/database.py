class Database:
    def __init__(self):
        self._base = {}
        self._tx_stack = []

    def set(self, key, value):
        if self._tx_stack:
            self._tx_stack[-1][key] = value
        else:
            self._base[key] = value

    def get(self, key):
        for tx in reversed(self._tx_stack):
            if key in tx:
                v = tx[key]
                if v is _DELETED:
                    return None
                return v
        return self._base.get(key)

    def delete(self, key):
        if not self._tx_stack:
            self._base.pop(key, None)
        else:
            self._tx_stack[-1][key] = _DELETED

    def count(self, value):
        all_keys = set(self._base.keys())
        for tx in self._tx_stack:
            all_keys.update(tx.keys())
        n = 0
        for k in all_keys:
            v = self.get(k)
            if v == value:
                n += 1
        return n

    def begin(self):
        self._tx_stack.append({})

    def rollback(self):
        if not self._tx_stack:
            return False
        self._tx_stack.pop()
        return True

    def commit(self):
        if not self._tx_stack:
            return False
        for tx in self._tx_stack:
            for k, v in tx.items():
                if v is _DELETED:
                    self._base.pop(k, None)
                else:
                    self._base[k] = v
        self._tx_stack.clear()
        return True


_DELETED = object()
