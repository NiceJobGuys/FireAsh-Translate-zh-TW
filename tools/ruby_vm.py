"""Small native Ruby bridge shared by source extraction and regression checks."""
import ctypes
import os


class RubyVM:
    def __init__(self, game):
        self.directory = os.add_dll_directory(str(game))
        self.lib = ruby = ctypes.CDLL(str(game / "x64-msvcrt-ruby300.dll"))
        self.stack = ctypes.c_void_p()
        ruby.ruby_init_stack.argtypes = [ctypes.c_void_p]
        ruby.ruby_init_stack(ctypes.byref(self.stack))
        ruby.ruby_setup.restype = ctypes.c_int
        if ruby.ruby_setup() != 0:
            raise RuntimeError("Ruby initialization failed")
        os.environ.pop("RUBYOPT", None)
        ruby.ruby_options.argtypes = [ctypes.c_int, ctypes.POINTER(ctypes.c_char_p)]
        ruby.ruby_options.restype = ctypes.c_void_p
        argv = (ctypes.c_char_p * 5)(b"ruby", b"--disable-gems", b"-e", b"", None)
        ruby.ruby_options(4, argv)
        ruby.rb_eval_string_protect.argtypes = [ctypes.c_char_p, ctypes.POINTER(ctypes.c_int)]
        ruby.rb_eval_string_protect.restype = ctypes.c_size_t
        ruby.rb_string_value_cstr.argtypes = [ctypes.POINTER(ctypes.c_size_t)]
        ruby.rb_string_value_cstr.restype = ctypes.c_char_p
        ruby.rb_errinfo.restype = ctypes.c_size_t
        ruby.rb_obj_as_string.argtypes = [ctypes.c_size_t]
        ruby.rb_obj_as_string.restype = ctypes.c_size_t
        ruby.rb_utf8_str_new.argtypes = [ctypes.c_char_p, ctypes.c_longlong]
        ruby.rb_utf8_str_new.restype = ctypes.c_size_t
        ruby.rb_gv_set.argtypes = [ctypes.c_char_p, ctypes.c_size_t]

    def put(self, name, value):
        value = value.encode("utf-8")
        self.lib.rb_gv_set(name.encode(), self.lib.rb_utf8_str_new(value, len(value)))

    def evaluate(self, code):
        state = ctypes.c_int()
        value = ctypes.c_size_t(self.lib.rb_eval_string_protect(
            ("# encoding: UTF-8\n" + code).encode(), ctypes.byref(state)))
        if state.value:
            error = ctypes.c_size_t(self.lib.rb_obj_as_string(self.lib.rb_errinfo()))
            raise RuntimeError(self.lib.rb_string_value_cstr(ctypes.byref(error)).decode())
        return self.lib.rb_string_value_cstr(ctypes.byref(value)).decode()
