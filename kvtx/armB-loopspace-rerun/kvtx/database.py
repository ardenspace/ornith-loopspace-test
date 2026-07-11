class Store:
    def __init__(self):
        self._kv: dict[str, str] = {}
        self._vk: dict[str, set[str]] = {}

    def set(self, key: str, value: str) -> None:
        old = self._kv.get(key)
        if old is not None:
            self._vk[old].discard(key)
            if not self._vk[old]:
                del self._vk[old]
        self._kv[key] = value
        self._vk.setdefault(value, set()).add(key)

    def get(self, key: str) -> str | None:
        return self._kv.get(key)

    def delete(self, key: str) -> None:
        old = self._kv.pop(key, None)
        if old is not None:
            self._vk[old].discard(key)
            if not self._vk[old]:
                del self._vk[old]

    def count(self, value: str) -> int:
        members = self._vk.get(value)
        return len(members) if members is not None else 0


class Database:
    def __init__(self):
        self._store = Store()
        self._tx_stack: list[dict[str, str | None]] = []

    def set(self, key: str, value: str) -> None:
        if self._tx_stack:
            self._tx_stack[-1][key] = value
        else:
            self._store.set(key, value)

    def get(self, key: str) -> str | None:
        for tx in reversed(self._tx_stack):
            if key in tx:
                return tx[key]
        return self._store.get(key)

    def delete(self, key: str) -> None:
        if self._tx_stack:
            self._tx_stack[-1][key] = None
        else:
            self._store.delete(key)

    def count(self, value: str) -> int:
        keys = set(self._store._kv.keys())
        for tx in self._tx_stack:
            keys.update(tx.keys())
        count = 0
        for key in keys:
            if self.get(key) == value:
                count += 1
        return count

    def begin(self) -> None:
        self._tx_stack.append({})

    def rollback(self) -> bool:
        if self._tx_stack:
            self._tx_stack.pop()
            return True
        return False

    def commit(self) -> bool:
        if self._tx_stack:
            for tx in self._tx_stack:
                for key, value in tx.items():
                    if value is None:
                        self._store.delete(key)
                    else:
                        self._store.set(key, value)
            self._tx_stack.clear()
            return True
        return False
