#!/usr/bin/env python

# Copyright (c) 2017, DIANA-HEP
# All rights reserved.
# 
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
# 
# * Redistributions of source code must retain the above copyright notice, this
#   list of conditions and the following disclaimer.
# 
# * Redistributions in binary form must reproduce the above copyright notice,
#   this list of conditions and the following disclaimer in the documentation
#   and/or other materials provided with the distribution.
# 
# * Neither the name of the copyright holder nor the names of its
#   contributors may be used to endorse or promote products derived from
#   this software without specific prior written permission.
# 
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
# FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
# DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
# SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
# OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import unittest

import numpy

import uproot

class TestCompression(unittest.TestCase):
    def runTest(self):
        pass
    
    def test_compression_identity(self):
        self.assertEqual(uproot.open("tests/Zmumu-zlib.root").compression.algo, "zlib")
        self.assertEqual(uproot.open("tests/Zmumu-zlib.root").compression.level, 4)

        self.assertEqual(uproot.open("tests/Zmumu-lzma.root").compression.algo, "lzma")
        self.assertEqual(uproot.open("tests/Zmumu-lzma.root").compression.level, 4)

        self.assertEqual(uproot.open("tests/Zmumu-lz4.root").compression.algo, "lz4")
        self.assertEqual(uproot.open("tests/Zmumu-lz4.root").compression.level, 4)

        self.assertEqual(uproot.open("tests/Zmumu-uncompressed.root").compression.level, 0)

        self.assertEqual(uproot.open("tests/HZZ-zlib.root").compression.algo, "zlib")
        self.assertEqual(uproot.open("tests/HZZ-zlib.root").compression.level, 4)

        self.assertEqual(uproot.open("tests/HZZ-lzma.root").compression.algo, "lzma")
        self.assertEqual(uproot.open("tests/HZZ-lzma.root").compression.level, 4)

        self.assertEqual(uproot.open("tests/HZZ-lz4.root").compression.algo, "lz4")
        self.assertEqual(uproot.open("tests/HZZ-lz4.root").compression.level, 4)

        self.assertEqual(uproot.open("tests/HZZ-uncompressed.root").compression.level, 0)

    def test_compression_keys(self):
        keys = uproot.open("tests/Zmumu-uncompressed.root").contents
        self.assertEqual(uproot.open("tests/Zmumu-zlib.root").contents, keys)
        self.assertEqual(uproot.open("tests/Zmumu-lzma.root").contents, keys)
        self.assertEqual(uproot.open("tests/Zmumu-lz4.root").contents, keys)

        keys = uproot.open("tests/HZZ-uncompressed.root").contents
        self.assertEqual(uproot.open("tests/HZZ-zlib.root").contents, keys)
        self.assertEqual(uproot.open("tests/HZZ-lzma.root").contents, keys)
        self.assertEqual(uproot.open("tests/HZZ-lz4.root").contents, keys)

    def test_compression_branches(self):
        branches = uproot.open("tests/Zmumu-uncompressed.root")["events"].branchnames
        self.assertEqual(uproot.open("tests/Zmumu-zlib.root")["events"].branchnames, branches)
        self.assertEqual(uproot.open("tests/Zmumu-lzma.root")["events"].branchnames, branches)
        self.assertEqual(uproot.open("tests/Zmumu-lz4.root")["events"].branchnames, branches)

        branches = uproot.open("tests/HZZ-uncompressed.root")["events"].branchnames
        self.assertEqual(uproot.open("tests/HZZ-zlib.root")["events"].branchnames, branches)
        self.assertEqual(uproot.open("tests/HZZ-lzma.root")["events"].branchnames, branches)
        self.assertEqual(uproot.open("tests/HZZ-lz4.root")["events"].branchnames, branches)

    def test_compression_content(self):    
        for name, array in uproot.open("tests/Zmumu-uncompressed.root")["events"].arrays().items():
            self.assertTrue(numpy.array_equal(uproot.open("tests/Zmumu-zlib.root")["events"].array(name), array))
            self.assertTrue(numpy.array_equal(uproot.open("tests/Zmumu-lzma.root")["events"].array(name), array))
            self.assertTrue(numpy.array_equal(uproot.open("tests/Zmumu-lz4.root")["events"].array(name), array))

        array = uproot.open("tests/HZZ-uncompressed.root")["events"].array("Electron_Px")
        self.assertTrue(numpy.array_equal(uproot.open("tests/HZZ-zlib.root")["events"].array("Electron_Px"), array))
        self.assertTrue(numpy.array_equal(uproot.open("tests/HZZ-lzma.root")["events"].array("Electron_Px"), array))
        self.assertTrue(numpy.array_equal(uproot.open("tests/HZZ-lz4.root")["events"].array("Electron_Px"), array))
