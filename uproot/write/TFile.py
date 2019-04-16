#!/usr/bin/env python

# BSD 3-Clause License; see https://github.com/scikit-hep/uproot/blob/master/LICENSE

import os
import sys
import struct
import uuid

import uproot_methods.convert

import uproot.const
import uproot.source.file
import uproot.write.sink.file
import uproot.write.sink.cursor
import uproot.write.TFree
import uproot.write.TKey
import uproot.write.TDirectory
import uproot.write.streamers
from uproot.rootio import nofilter

class TFileUpdate(object):
    def __init__(self, path):
        self._openfile(path)
        raise NotImplementedError

    def _openfile(self, path, compressionAlgorithm, compressionLevel):
        if isinstance(path, getattr(os, "PathLike", ())):
            path = os.fspath(path)
        elif hasattr(path, "__fspath__"):
            path = path.__fspath__()
        elif path.__class__.__module__ == "pathlib":
            import pathlib
            if isinstance(path, pathlib.Path):
                 path = str(path)

        self.compressionAlgorithm = compressionAlgorithm
        self.compressionLevel = compressionLevel

        self._sink = uproot.write.sink.file.FileSink(path)
        self._path = path
        self._filename = os.path.split(path)[1].encode("utf-8")

    @staticmethod
    def _normalizewhere(where):
        if (sys.version_info[0] <= 2 and isinstance(where, unicode)) or (sys.version_info[0] > 2 and isinstance(where, str)):
            where = where.encode("utf-8")
        if not isinstance(where, bytes):
            raise TypeError("ROOT file key must be a string")

        if b";" in where:
            at = where.rindex(b";")
            where, cycle = where[:at], where[at + 1:]
            cycle = int(cycle)
        else:
            cycle = None

        if b"/" in where:
            raise NotImplementedError("subdirectories not supported yet")

        return where, cycle

    def __setitem__(self, where, what):
        where, cycle = self._normalizewhere(where)
        what = uproot_methods.convert.towriteable(what)
        cursor = uproot.write.sink.cursor.Cursor(self._fSeekFree)
        newkey = uproot.write.TKey.TKey(fClassName = what.fClassName,
                                        fName      = where,
                                        fTitle     = what.fTitle,
                                        fObjlen    = what.length(where),
                                        fSeekKey   = self._fSeekFree,
                                        fSeekPdir  = self._fBEGIN,
                                        fCycle     = cycle if cycle is not None else self._rootdir.newcycle(where))

        newkey.write(cursor, self._sink)
        what.write(cursor, self._sink, where)
        self._expandfile(cursor)

        self._rootdir.setkey(newkey)
        self._sink.flush()

    def __delitem__(self, where):
        where, cycle = self._normalizewhere(where)
        try:
            self._rootdir.delkey(where, cycle)
        except KeyError:
            raise KeyError("ROOT directory does not contain key {0}".format(where))

    def _reopen(self):
        return uproot.open(self._path, localsource=lambda path: uproot.source.file.FileSource(path, **uproot.source.file.FileSource.defaults))

    @property
    def compression(self):
        return self._reopen().compression

    def __repr__(self):
        return "<{0} {1} at 0x{2:012x}>".format(self.__class__.__name__, repr(self._filename), id(self))

    def __getitem__(self, name):
        return self._reopen().get(name)

    def __len__(self):
        return len(self._reopen()._keys)

    def __iter__(self):
        return self._reopen().iterkeys()

    def showstreamers(self, filtername=nofilter, stream=sys.stdout):
        return self._reopen().showstreamers(filtername=filtername, stream=stream)

    def iterkeys(self, recursive=False, filtername=nofilter, filterclass=nofilter):
        return self._reopen().iterkeys(recursive=recursive, filtername=filtername, filterclass=filterclass)

    def itervalues(self, recursive=False, filtername=nofilter, filterclass=nofilter):
        return self._reopen().itervalues(recursive=recursive, filtername=filtername, filterclass=filterclass)

    def iteritems(self, recursive=False, filtername=nofilter, filterclass=nofilter):
        return self._reopen().iteritems(recursive=recursive, filtername=filtername, filterclass=filterclass)

    def iterclasses(self, recursive=False, filtername=nofilter, filterclass=nofilter):
        return self._reopen().iterclasses(recursive=recursive, filtername=filtername, filterclass=filterclass)

    def keys(self, recursive=False, filtername=nofilter, filterclass=nofilter):
        return self._reopen().keys(recursive=recursive, filtername=filtername, filterclass=filterclass)

    def _ipython_key_completions_(self):
        "Support for completion of keys in an IPython kernel"
        return self._reopen()._ipython_key_completions_()

    def values(self, recursive=False, filtername=nofilter, filterclass=nofilter):
        return self._reopen().values(recursive=recursive, filtername=filtername, filterclass=filterclass)

    def items(self, recursive=False, filtername=nofilter, filterclass=nofilter):
        return self._reopen().items(recursive=recursive, filtername=filtername, filterclass=filterclass)

    def classes(self, recursive=False, filtername=nofilter, filterclass=nofilter):
        return self._reopen().classes(recursive=recursive, filtername=filtername, filterclass=filterclass)

    def allkeys(self, filtername=nofilter, filterclass=nofilter):
        return self._reopen().allkeys(filtername=filtername, filterclass=filterclass)

    def allvalues(self, filtername=nofilter, filterclass=nofilter):
        return self._reopen().allvalues(filtername=filtername, filterclass=filterclass)

    def allitems(self, filtername=nofilter, filterclass=nofilter):
        return self._reopen().allitems(filtername=filtername, filterclass=filterclass)

    def allclasses(self, filtername=nofilter, filterclass=nofilter):
        return self._reopen().allclasses(filtername=filtername, filterclass=filterclass)

    def get(self, name, cycle=None):
        return self._reopen().get(name, cycle=cycle)

    def __contains__(self, name):
        return name in self._reopen()

    def __getitem__(self, where):
        return self._reopen()[where]

    @property
    def closed(self):
        return self._sink.closed

    def close(self):
        self._sink.close()

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        self.close()

class TFileRecreate(TFileUpdate):
    def __init__(self, path, compressionAlgorithm=uproot.const.kZLIB, compressionLevel=1):
        self._openfile(path, compressionAlgorithm, compressionLevel)
        self._writeheader()
        self._writerootdir()
        self._writestreamers()
        self._writerootkeys()
        self._sink.flush()

    _format1           = struct.Struct(">4sii")
    _format_end        = struct.Struct(">qqii")
    _format2           = struct.Struct(">iB")
    _format3           = struct.Struct(">i")
    _format_seekinfo   = struct.Struct(">q")
    _format_nbytesinfo = struct.Struct(">i")

    def getcompression(self):
        algo = max(self.fCompress // 100, uproot.const.kZLIB)
        level = self.fCompress % 100
        return algo, level

    def compression(self, compressionAlgorithm=uproot.const.kZLIB, compressionLevel=1): # Replace with 1 when compression works
        return (compressionAlgorithm * 100) + compressionLevel

    def updateCompression(self, compressionAlgorithm=uproot.const.kZLIB, compressionLevel=1): # Replace with 1 when compression works
        self.fCompress = self.compression(compressionAlgorithm=compressionAlgorithm, compressionLevel=compressionLevel)
        self.compresscursor.update_fields(self._sink, self._format3, self.fCompress)
        self._writestreamers()

    def _writeheader(self):
        cursor = uproot.write.sink.cursor.Cursor(0)
        self._fVersion = self._fVersion = 1061404
        self._fBEGIN = 100
        cursor.write_fields(self._sink, self._format1, b"root", self._fVersion, self._fBEGIN)

        self._fEND = 0
        self._fSeekFree = 0
        self._fNbytesFree = 0
        self._nfree = 0
        self._endcursor = uproot.write.sink.cursor.Cursor(cursor.index)
        cursor.write_fields(self._sink, self._format_end, self._fEND, self._fSeekFree, self._fNbytesFree, self._nfree)

        self._fNbytesName = 2*len(self._filename) + 36 + 8   # + 8 because two fields in TKey are 'q' rather than 'i'
        fUnits = 4
        cursor.write_fields(self._sink, self._format2, self._fNbytesName, fUnits)

        self.compresscursor = uproot.write.sink.cursor.Cursor(cursor.index)
        self.fCompress = self.compression(compressionAlgorithm=self.compressionAlgorithm, compressionLevel=self.compressionLevel)
        cursor.write_fields(self._sink, self._format3, self.fCompress)

        self._fSeekInfo = 0
        self._seekcursor = uproot.write.sink.cursor.Cursor(cursor.index)
        cursor.write_fields(self._sink, self._format_seekinfo, self._fSeekInfo)

        self._fNbytesInfo = 0
        self._nbytescursor = uproot.write.sink.cursor.Cursor(cursor.index)
        cursor.write_fields(self._sink, self._format_nbytesinfo, self._fNbytesInfo)

        cursor.write_data(self._sink, b'\x00\x01' + uuid.uuid1().bytes)

    def _expandfile(self, cursor):
        if cursor.index > self._fSeekFree:
            freecursor = uproot.write.sink.cursor.Cursor(cursor.index)
            freekey = uproot.write.TKey.TKey(b"TFile", self._filename, fObjlen=0, fSeekKey=cursor.index, fSeekPdir=self._fBEGIN)
            freeseg = uproot.write.TFree.TFree(cursor.index + freekey.fNbytes)
            freekey.fObjlen = freeseg.size()

            freekey.write(freecursor, self._sink)
            freeseg.write(freecursor, self._sink)

            self._fSeekFree = cursor.index
            self._fEND = cursor.index + freekey.fNbytes
            self._fNbytesFree = freekey.fNbytes
            self._nfree = 1
            self._endcursor.update_fields(self._sink, self._format_end, self._fEND, self._fSeekFree, self._fNbytesFree, self._nfree)

    def _writerootdir(self):
        cursor = uproot.write.sink.cursor.Cursor(self._fBEGIN)

        self._rootdir = uproot.write.TDirectory.TDirectory(self, self._filename, self._fNbytesName)

        key = uproot.write.TKey.TKey(b"TFile", self._filename, fObjlen=self._rootdir.size())
        key.write(cursor, self._sink)
        self._rootdir.write(cursor, self._sink)

        self._expandfile(cursor)

    def _writestreamers(self):
        self._fSeekInfo = self._fSeekFree
        self._seekcursor.update_fields(self._sink, self._format_seekinfo, self._fSeekInfo)

        cursor = uproot.write.sink.cursor.Cursor(self._fSeekInfo)
        streamerkey = uproot.write.TKey.TKey32(fClassName = b"TList",
                                               fName      = b"StreamerInfo",
                                               fTitle     = b"Doubly linked list",
                                               fObjlen    = len(uproot.write.streamers.streamers),
                                               fSeekKey   = self._fSeekInfo,
                                               fSeekPdir  = self._fBEGIN)
        streamerkeycursor = uproot.write.sink.cursor.Cursor(self._fSeekInfo)
        streamerkey.write(cursor, self._sink)

        _header = struct.Struct("2sBBBBBBB")
        algorithm, level = self.getcompression()
        uncompressedbytes = len(uproot.write.streamers.streamers)
        u1 = (uncompressedbytes >> 0) & 0xff
        u2 = (uncompressedbytes >> 8) & 0xff
        u3 = (uncompressedbytes >> 16) & 0xff
        fNbytes = streamerkey.fNbytes
        if level > 0:
            if algorithm == uproot.const.kZLIB:
                algo = b"ZL"
                import zlib
                compressedbytes = len(zlib.compress(uproot.write.streamers.streamers, level=level))
                if compressedbytes <= uncompressedbytes:
                    c1 = (compressedbytes >> 0) & 0xff
                    c2 = (compressedbytes >> 8) & 0xff
                    c3 = (compressedbytes >> 16) & 0xff
                    method = 8
                    cursor.write_fields(self._sink, _header, algo, method, c1, c2, c3, u1, u2, u3)
                    cursor.write_data(self._sink, zlib.compress(uproot.write.streamers.streamers, level=level))
                    fNbytes = compressedbytes + streamerkey.fKeylen + 9
                    streamerkey.write(streamerkeycursor, self._sink, fNbytes)
            elif algorithm == uproot.const.kLZ4:
                import xxhash
                algo = b"L4"
                try:
                    import lz4.frame
                except ImportError:
                    raise ImportError("Install lz4 package with:\n    pip install lz4\nor\n    conda install -c anaconda lz4")
                compressedbytes = len(lz4.frame.compress(uproot.write.streamers.streamers)) + 8
                if compressedbytes <= uncompressedbytes:
                    c1 = (compressedbytes >> 0) & 0xff
                    c2 = (compressedbytes >> 8) & 0xff
                    c3 = (compressedbytes >> 16) & 0xff
                    method = lz4.library_version_number() // (100 * 100)
                    checksum = xxhash.xxh64(uproot.write.streamers.streamers).digest()
                    cursor.write_fields(self._sink, _header, algo, method, c1, c2, c3, u1, u2, u3)
                    cursor.write_data(self._sink, checksum)
                    cursor.write_data(self._sink, lz4.frame.compress(uproot.write.streamers.streamers, compression_level=level))
                fNbytes = compressedbytes + streamerkey.fKeylen + 9
                streamerkey.write(streamerkeycursor, self._sink, fNbytes)
            elif algorithm == uproot.const.kLZMA:
                algo = b"XZ"
                try:
                    import lzma
                except ImportError:
                    try:
                        from backports import lzma
                    except ImportError:
                        raise ImportError("Install lzma package with:\n    pip install backports.lzma\nor\n    conda install -c conda-forge backports.lzma\n(or just use Python >= 3.3).")
                compressedbytes = len(lzma.compress(uproot.write.streamers.streamers, preset=level))
                if compressedbytes <= uncompressedbytes:
                    c1 = (compressedbytes >> 0) & 0xff
                    c2 = (compressedbytes >> 8) & 0xff
                    c3 = (compressedbytes >> 16) & 0xff
                    method = 0
                    cursor.write_fields(self._sink, _header, algo, method, c1, c2, c3, u1, u2, u3)
                    cursor.write_data(self._sink, lzma.compress(uproot.write.streamers.streamers, preset=level))
                    fNbytes = compressedbytes + streamerkey.fKeylen + 9
                    streamerkey.write(streamerkeycursor, self._sink, fNbytes)
            else:
                raise ValueError("Unrecognized compression algorithm: {0}".format(algorithm))
            self._fNbytesInfo = fNbytes
        else:
            cursor.write_data(self._sink, uproot.write.streamers.streamers)
            self._fNbytesInfo = streamerkey.fNbytes

        self._nbytescursor.update_fields(self._sink, self._format_nbytesinfo, self._fNbytesInfo)

        self._expandfile(cursor)

    def _writerootkeys(self):
        self._rootdir.writekeys(uproot.write.sink.cursor.Cursor(self._fSeekFree))

class TFileCreate(TFileRecreate):
    def __init__(self, path):
        if os.path.exists(path):
            raise OSError("file {} already exists".format(path))
        super(TFileCreate, self).__init__(path)
