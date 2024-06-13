#!/usr/bin/python
# -*- coding: utf-8 -*-

# adapted from https://github.com/parallel-fs-utils/multi-thread-posix/


import os
import errno
import multiprocessing
import time


# python generator to recursively walk directory tree
# looking for all subdirectories,
# returning child directories before their parents
# this allows us to construct list of directories to delete
# in parallel with threads that delete them.

def find_subdirs(d):
    entries = os.listdir(d)
    for e in entries:
        entry_path = os.path.join(d, e)
        if not os.path.islink(entry_path) and os.path.isdir(entry_path):
            for subd in find_subdirs(entry_path):
                yield subd
    yield d


class RmThread(multiprocessing.Process):

    def __init__(self, parent_conn_in, child_conn_in, index_in, topdir):
        self.index = index_in
        self.parent_conn = parent_conn_in
        self.child_conn = child_conn_in
        self.topdir = topdir

        self.file_count = 0
        self.dir_count = 0
        self.dir_remove_collisions = 0
        self.dir_remove_nonempty = 0
        multiprocessing.Process.__init__(self)

    def run(self):
        while [True]:
            d = self.child_conn.recv()
            if d == os.sep:
                break
            try:
                dir_contents = os.listdir(d)
            except OSError as e:
                if e.errno == errno.ENOENT:
                    self.dir_remove_collisions += 1
                    # not a problem, someone else might have removed
                    continue
                raise e

            # delete contents of directory
            # rather than have competing threads lock directories,
            # we rely on the filesystem to handle cases
            # where two threads attempt to delete at same time
            # one of the threads will get ENOENT in this case,
            # but that's ok, doesn't matter

            for dentry in dir_contents:
                de_path = os.path.join(d, dentry)
                if (not os.path.islink(de_path)) and os.path.isdir(de_path):
                    continue
                try:
                    os.unlink(de_path)
                    self.file_count += 1
                except OSError as e:
                    if e.errno == errno.ENOENT:
                        self.dir_remove_collisions += 1
                        continue
                    raise e

            # delete directory and non-empty parent directories up to topdir
            # we can't delete d if it contains a subdirectory
            # (that hasn't been deleted yet)
            # that's ok, we'll get ENOTEMPTY and stop
            # other threads could be doing this same thing
            # (e.g. thread that deleted child of d)
            # again, rely on filesystem to deal with this,
            # one thread gets an ENOENT exception
            # that's ok, just stop

            while len(d) >= len(self.topdir):
                try:
                    os.rmdir(d)
                    self.dir_count += 1
                except OSError as e:
                    if e.errno == errno.ENOTEMPTY:
                        self.dir_remove_nonempty += 1  # ok, will delete later
                        break
                    if e.errno == errno.ENOENT:
                        self.dir_remove_collisions += 1  # other thread did it
                        break
                    raise e
                d = os.path.dirname(d)

        self.child_conn.send((self.file_count, self.dir_count,
                             self.dir_remove_collisions,
                             self.dir_remove_nonempty))


def parallel_rm_rf(root_dir, process_count, verbose=True):
    start_time = time.time()
    worker_pool = []
    for n in range(0, process_count):
        (parent_conn, child_conn) = multiprocessing.Pipe()
        t = RmThread(parent_conn, child_conn, n, root_dir)
        worker_pool.append(t)
        t.daemon = True
        t.start()

    # round-robin schedule child threads to process directories
    # FIXME: we could do something much more intelligent later on
    # like scheduling based on total file count assigned to each thread

    index = 0
    for d in find_subdirs(root_dir):
        worker_pool[index].parent_conn.send(d)
        index += 1
        if index >= process_count:
            index = 0

    elapsed_time = time.time() - start_time
    if verbose:
        print('constructed directory list and awaiting thread completions ' +
              'after %9.2f sec' % elapsed_time)

    total_dirs = 0
    total_files = 0
    for worker in worker_pool:
        worker.parent_conn.send(os.sep)  # tell child that we're done
        (w_file_count, w_dir_count, w_dir_remove_collisions,
         w_dir_remove_nonempty) = worker.parent_conn.recv()
        worker.join()  # wait for child to exit
        if verbose:
            print(('after %7.2f sec process %d removed %d files and %d dirs ' +
                   'with %d collisions and %d non-empty dirs') % (
                  time.time() - start_time,
                  worker.index,
                  w_file_count,
                  w_dir_count,
                  w_dir_remove_collisions,
                  w_dir_remove_nonempty))
        total_dirs += w_dir_count
        total_files += w_file_count

    elapsed_time = time.time() - start_time
    if verbose:
        print('elapsed time = %7.2f sec' % elapsed_time)
    fps = total_files / elapsed_time
    if verbose:
        print('files per second = %8.2f' % fps)
    dps = total_dirs / elapsed_time
    if verbose:
        print('directories per second = %8.2f' % dps)
