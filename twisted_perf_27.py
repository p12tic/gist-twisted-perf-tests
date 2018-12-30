#!/usr/bin/env python3

import argparse
import json
import os
import sys
import time
import traceback
from functools import reduce

from twisted.internet import defer
from twisted.internet import reactor
from twisted.python import log
from functools import wraps

sys.path.append(os.path.dirname(__file__))
import perf_utils

defer_list = []
defer_is_blocked = [True]

def test_deferred(x):
    if defer_is_blocked[0]:
        d = defer.Deferred()
        defer_list.append((d, x))
        return d
    else:
        return defer.succeed(x)

@defer.inlineCallbacks
def test_inline_deferred(x):
    yield test_deferred(x)

def test_return_deferred(x):
    return test_deferred(x)

def func(x):
    return x

def gen_test_N_func(n):
    def test_N_func(x):
        for i in range(n):
            x = func(x)
        return x
    return test_N_func

def gen_test_N_deferred(n):
    def test_N_deferred(x):
        for i in range(n):
            test_deferred(x)
        return x
    return test_N_deferred

def gen_test_N_M_func(n, m):

    def impl(x):
        for i in range(m):
            x = func(x)
        return x

    def test_N_M_func(x):
        for i in range(n):
            x = impl(x)
        return x
    return test_N_M_func

def gen_test_N_M_deferred(n, m):

    def impl(x):
        for i in range(m):
            test_deferred(x)
        return x

    def test_N_M_deferred(x):
        for i in range(n):
            x = impl(x)
        return x
    return test_N_M_deferred

def gen_test_addCallback_N_succeed_func(n):
    def test_addCallback_N_succeed_func(x):
        d = defer.succeed(x)
        for i in range(n):
            d.addCallback(func)
        return d
    return test_addCallback_N_succeed_func

def gen_test_yield_N_func_succeed_returnValue(n):
    @defer.inlineCallbacks
    def test_yield_N_func_succeed_returnValue(x):
        x = yield defer.succeed(x)
        for i in range(n):
            x = yield func(x)
        defer.returnValue(x)
    return test_yield_N_func_succeed_returnValue

def gen_test_yield_N_func_succeed_returnValue(n):
    @defer.inlineCallbacks
    def test_yield_N_func_succeed_returnValue(x):
        x = yield defer.succeed(x)
        for i in range(n):
            x = yield func(x)
        defer.returnValue(x)
    return test_yield_N_func_succeed_returnValue

def gen_test_yield_N_func_returnValue(n):
    @defer.inlineCallbacks
    def test_yield_N_func_returnValue(x):
        for i in range(3):
            x = yield func(x)
        defer.returnValue(x)
    return test_yield_N_func_returnValue

def gen_test_addCallback_N_succeed_deferred(n):
    def test_addCallback_N_succeed_deferred(x):
        d = defer.succeed(x)
        for i in range(n):
            d.addCallback(test_deferred)
        return d
    return test_addCallback_N_succeed_deferred

def gen_test_yield_N_succeed_deferred_returnValue(n):
    @defer.inlineCallbacks
    def test_yield_N_succeed_deferred_returnValue(x):
        x = yield defer.succeed(x)
        for i in range(n):
            x = yield test_deferred(x)
        defer.returnValue(x)
    return test_yield_N_succeed_deferred_returnValue

def gen_test_yield_N_deferred_returnValue(n):
    @defer.inlineCallbacks
    def test_yield_N_deferred_returnValue(x):
        for i in range(n):
            x = yield test_deferred(x)
        defer.returnValue(x)
    return test_yield_N_deferred_returnValue

def gen_test_yield_N_yield_M_func_returnValue(n, m):

    @defer.inlineCallbacks
    def impl1(x):
        x = yield func(x)
        defer.returnValue(x)

    @defer.inlineCallbacks
    def impl2(x):
        for i in range(m):
            x = yield impl1(x)
        defer.returnValue(x)

    @defer.inlineCallbacks
    def test_yield_N_yield_M_func_returnValue(x):
        for i in range(n):
            x = yield impl2(x)
        defer.returnValue(x)
    return test_yield_N_yield_M_func_returnValue

def gen_test_yield_N_yield_M_deferred_returnValue(n, m):

    @defer.inlineCallbacks
    def impl1(x):
        x = yield test_deferred(x)
        defer.returnValue(x)

    @defer.inlineCallbacks
    def impl2(x):
        for i in range(m):
            x = yield impl1(x)
        defer.returnValue(x)

    @defer.inlineCallbacks
    def test_yield_N_yield_M_deferred_returnValue(x):
        for i in range(n):
            x = yield impl2(x)
        defer.returnValue(x)
    return test_yield_N_yield_M_deferred_returnValue


def do_single_test(test_fn, callback_count, is_blocked):
    defer_is_blocked[0] = is_blocked

    d = defer.Deferred()

    for i in range(callback_count):
        d.addCallback(test_fn)
    d.addErrback(log.err)
    d.callback(1)
    for df, x in defer_list:
        df.callback(x)
    del defer_list[:]
    return d

@defer.inlineCallbacks
def do_tests(result_path):
    try:
        #yield do_single_test(test_deferred, 100000)
        #'''

        # each entry is a tuple of:
        # - name of the function to test
        # - the function to test
        # - the name of the "base" function to test against, or None
        # - the test count multiplier
        # - whether the test deferreds are "blocked" or have their .callback
        #   already called.
        #
        # The base function should run only the testing overheads equivalent to
        # the function under test.
        simple_test_functions = [
            ('warmup', test_deferred, None, 1, True),
            ('test_deferred', test_deferred, None, 1, False),
            ('test_deferred_blocked', test_deferred, None, 1, True),
            ('test_inline_deferred', test_inline_deferred, 'test_deferred', 1, False),
            ('test_inline_deferred_blocked', test_inline_deferred, 'test_deferred', 1, True),
            ('test_return_deferred', test_return_deferred, 'test_deferred', 1, False),
        ]

        # gen_test_functions: A list of tuples identifying tests to generate.
        #
        # The first member of each tuple is a function that accepts one or more
        # integers and returns a function that would execute something the given
        # number of times. The generated functions are identified by their
        # names: _N_ is replaced by the value of the first argument passed to
        # the function generator, _M_ is replaced by the second.
        #
        # The second member is the name of the "base" function, _N_ and _M_
        # replacements will be done on it to acquire the name of the final
        # base function.
        #
        # The third member is the test count multiplier.
        #
        # The fourth member is a list of tuples that identify data to pass
        # to the first function to generate actual functions to test.

        gen_args_n = [(1,), (3,), (10,)]
        gen_args_n_m = [(1, 1), (1, 3), (3, 1), (3, 3), (10, 1), (10, 3), (10, 10)]

        gen_test_functions = [
            (gen_test_N_func, None, 1, gen_args_n),
            (gen_test_N_M_func, None, 1, gen_args_n_m),
            (gen_test_N_deferred, None, 1, gen_args_n),
            (gen_test_N_M_deferred, None, 1, gen_args_n_m),
            (gen_test_addCallback_N_succeed_func, 'test_N_func', 1, gen_args_n),
            (gen_test_yield_N_func_returnValue, 'test_N_func', 1, gen_args_n),
            (gen_test_yield_N_yield_M_func_returnValue, 'test_N_M_func', 1, gen_args_n_m),
            (gen_test_addCallback_N_succeed_deferred, 'test_N_deferred', 1, gen_args_n),
            (gen_test_yield_N_succeed_deferred_returnValue, 'test_N_deferred', 1, gen_args_n),
            (gen_test_yield_N_deferred_returnValue, 'test_N_deferred', 1, gen_args_n),
            (gen_test_yield_N_yield_M_deferred_returnValue, 'test_N_M_deferred', 1, gen_args_n_m),
        ]

        test_count = 500
        callback_count = 1000

        function_timings = {}

        test_functions = simple_test_functions[:]

        def replace_args_function_name(fn, args, is_blocked):
            if fn is None:
                return None
            names = ['_N_', '_M_']
            for name, arg in zip(names, args):
                fn = fn.replace(name, '_{0}_'.format(arg))
            if is_blocked:
                fn += '_blocked'
            return fn

        for gen, base_fun_name, count_mult, gen_args in gen_test_functions:
            for args in gen_args:
                fun = gen(*args)

                blocked_args = [False]
                if '_deferred' in gen.__name__:
                    blocked_args = [True, False]

                for is_blocked in blocked_args:
                    fun_name = gen.__name__.replace('gen_', '')
                    fun_name = replace_args_function_name(fun_name, args, is_blocked)
                    this_base_fun_name = replace_args_function_name(base_fun_name, args, is_blocked)
                    this_count_mult = float(count_mult) / reduce((lambda a, b: a * b), args)
                    test_functions.append((fun_name, fun, this_base_fun_name, this_count_mult, is_blocked))

        results = perf_utils.PerfResults()

        for fun_name, test_fn, base_fun_name, count_mult, is_blocked in test_functions:
            print('Measuring {}'.format(fun_name))

            this_test_count = max(1, int(test_count * count_mult))

            start = time.time()
            for n in range(this_test_count):
                yield do_single_test(test_fn, callback_count, is_blocked)
            end = time.time()
            per_cb_us = (end - start) * 1000000 / (this_test_count * callback_count)
            results.add(fun_name, per_cb_us, base_fun_name)

        print(results.get_results_str())
        if result_path is not None:
            with open(result_path, 'w') as out_f:
                json.dump(results.to_json(), out_f, indent=2, sort_keys=True)
    except:
        traceback.print_exc()
    finally:
        yield reactor.stop()

def main():
    parser = argparse.ArgumentParser(prog='twisted_perf_27')
    parser.add_argument('path', type=str, default=None, nargs='?',
                        help="Output data path")
    args = parser.parse_args()

    reactor.callLater(0, do_tests, args.path)
    reactor.run()

if __name__ == '__main__':
    main()
