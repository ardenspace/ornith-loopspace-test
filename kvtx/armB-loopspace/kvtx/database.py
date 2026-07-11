"""In-memory key-value store with value-count tracking and nested transactions."""

_DELETED = object()


class Store:
    """A key-value store that also tracks how many keys map to each value.

    All operations are O(1) and reflect the current visible state, including
    uncommitted changes in open transactions.
    """

    def __init__(self):
        self._kv: dict[str, str] = {}
        self._vk: dict[str, int] = {}

    def set(self, key: str, value: str) -> None:
        """Record that key currently maps to value (creating or overwriting)."""
        if key in self._kv:
            old_value = self._kv[key]
            self._vk[old_value] -= 1
            if self._vk[old_value] == 0:
                del self._vk[old_value]
        self._kv[key] = value
        self._vk[value] = self._vk.get(value, 0) + 1

    def get(self, key: str) -> str | None:
        """Return the current value of key, or None if key is not set."""
        return self._kv.get(key)

    def delete(self, key: str) -> None:
        """Make key not set. Deleting an unset key is a no-op."""
        if key not in self._kv:
            return
        value = self._kv.pop(key)
        self._vk[value] -= 1
        if self._vk[value] == 0:
            del self._vk[value]

    def count(self, value: str) -> int:
        """Return the number of keys whose current value equals value."""
        return self._vk.get(value, 0)


class Database:
    """Key-value store with nested transaction support.

    Transactions nest: begin() pushes a frame, rollback() pops the innermost
    frame (restoring state), commit() applies all frames to base state and
    clears the stack. Reads see uncommitted writes via an overlay model.
    """

    def __init__(self):
        self._kv: dict[str, str] = {}
        self._vk: dict[str, int] = {}
        self._tx_stack: list[dict[str, object]] = []

    def set(self, key: str, value: str) -> None:
        """Record that key currently maps to value (creating or overwriting)."""
        if self._tx_stack:
            self._tx_stack[-1][key] = value
        else:
            old_value = self._kv.get(key)
            if old_value is not None:
                self._vk[old_value] -= 1
                if self._vk[old_value] == 0:
                    del self._vk[old_value]
            self._kv[key] = value
            self._vk[value] = self._vk.get(value, 0) + 1

    def get(self, key: str) -> str | None:
        """Return the current value of key, or None if key is not set."""
        for frame in reversed(self._tx_stack):
            if key in frame:
                val = frame[key]
                return None if val is _DELETED else val
        return self._kv.get(key)

    def delete(self, key: str) -> None:
        """Make key not set. Deleting an unset key is a no-op."""
        if self._tx_stack:
            self._tx_stack[-1][key] = _DELETED
        else:
            if key not in self._kv:
                return
            value = self._kv.pop(key)
            self._vk[value] -= 1
            if self._vk[value] == 0:
                del self._vk[value]

    def count(self, value: str) -> int:
        """Return the number of keys whose current value equals value."""
        keys = set(self._kv.keys())
        for frame in self._tx_stack:
            keys.update(frame.keys())
        count = 0
        for key in keys:
            if self.get(key) == value:
                count += 1
        return count

    def begin(self) -> None:
        """Open a new transaction frame."""
        self._tx_stack.append({})

    def rollback(self) -> bool:
        """Discard the innermost transaction. Returns True if one was open."""
        if not self._tx_stack:
            return False
        self._tx_stack.pop()
        return True

    def commit(self) -> bool:
        """Apply all open transactions to base state. Returns True if any were open."""
        if not self._tx_stack:
            return False
        for frame in self._tx_stack:
            for key, val in frame.items():
                if val is _DELETED:
                    old = self._kv.get(key)
                    if old is not None:
                        self._vk[old] -= 1
                        if self._vk[old] == 0:
                            del self._vk[old]
                        del self._kv[key]
                else:
                    old = self._kv.get(key)
                    if old is not None:
                        self._vk[old] -= 1
                        if self._vk[old] == 0:
                            del self._vk[old]
                    self._kv[key] = val
                    self._vk[val] = self._vk.get(val, 0) + 1
        self._tx_stack.clear()
        return True
