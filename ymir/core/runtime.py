import ctypes
import socket


# Memory management from previous example
class YmirObject(ctypes.Structure):
    _fields_ = [("ref_count", ctypes.c_int)]


class MemoryManager:
    def __init__(self):
        self.objects = []

    def allocate(self, size: int) -> ctypes.c_void_p:
        obj = ctypes.create_string_buffer(size)
        ymir_obj = YmirObject.from_buffer(obj)
        ymir_obj.ref_count = 1
        self.objects.append(obj)
        return ctypes.cast(ctypes.pointer(obj), ctypes.c_void_p)

    def retain(self, obj: ctypes.c_void_p) -> None:
        ymir_obj = YmirObject.from_buffer(
            ctypes.cast(obj, ctypes.POINTER(ctypes.c_char * ctypes.sizeof(YmirObject))).contents
        )
        ymir_obj.ref_count += 1

    def release(self, obj: ctypes.c_void_p) -> None:
        ymir_obj = YmirObject.from_buffer(
            ctypes.cast(obj, ctypes.POINTER(ctypes.c_char * ctypes.sizeof(YmirObject))).contents
        )
        ymir_obj.ref_count -= 1
        if ymir_obj.ref_count == 0:
            self.objects.remove(ctypes.cast(obj, ctypes.POINTER(ctypes.c_char)).contents)


memory_manager = MemoryManager()


# Networking functions
def ymir_socket(domain: int, type: int, protocol: int) -> ctypes.c_void_p:
    sock = socket.socket(domain, type, protocol)
    return ctypes.cast(ctypes.py_object(sock), ctypes.c_void_p)


def ymir_connect(sock_ptr: ctypes.c_void_p, address_ptr: ctypes.c_char_p, address_len: int) -> int:
    sock = ctypes.cast(sock_ptr, ctypes.py_object).value
    address = address_ptr.decode("utf-8")
    return sock.connect((address, address_len))


def ymir_send(sock_ptr: ctypes.c_void_p, buffer_ptr: ctypes.c_char_p, length: int) -> int:
    sock = ctypes.cast(sock_ptr, ctypes.py_object).value
    buffer = ctypes.cast(buffer_ptr, ctypes.POINTER(ctypes.c_char * length))
    return sock.send(buffer.contents.raw)


def ymir_recv(sock_ptr: ctypes.c_void_p, buffer_ptr: ctypes.c_void_p, length: int) -> int:
    sock = ctypes.cast(sock_ptr, ctypes.py_object).value
    buffer = ctypes.create_string_buffer(length)
    num_received = sock.recv_into(buffer, length)
    ctypes.memmove(buffer_ptr, buffer, num_received)
    return num_received


def ymir_close(sock_ptr: ctypes.c_void_p) -> int:
    sock = ctypes.cast(sock_ptr, ctypes.py_object).value
    sock.close()
    return 0


# Mapping runtime functions to names
runtime_functions = {
    "socket": ymir_socket,
    "connect": ymir_connect,
    "send": ymir_send,
    "recv": ymir_recv,
    "close": ymir_close,
}

# Expose runtime functions to LLVM
llvm_runtime_functions = {
    "socket": ctypes.CFUNCTYPE(ctypes.c_void_p, ctypes.c_int, ctypes.c_int, ctypes.c_int)(ymir_socket),
    "connect": ctypes.CFUNCTYPE(ctypes.c_int, ctypes.c_void_p, ctypes.c_char_p, ctypes.c_int)(ymir_connect),
    "send": ctypes.CFUNCTYPE(ctypes.c_int, ctypes.c_void_p, ctypes.c_char_p, ctypes.c_int)(ymir_send),
    "recv": ctypes.CFUNCTYPE(ctypes.c_int, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_int)(ymir_recv),
    "close": ctypes.CFUNCTYPE(ctypes.c_int, ctypes.c_void_p)(ymir_close),
}


def get_runtime_function(name: str) -> ctypes.CFUNCTYPE:
    return llvm_runtime_functions.get(name)


# Initialize the runtime environment
def initialize_runtime() -> None:
    pass


# Finalize the runtime environment
def finalize_runtime() -> None:
    pass
