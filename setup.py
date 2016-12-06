#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import with_statement
from __future__ import print_function

import sys
import os
import os.path
import math
import platform
import re
import subprocess
import traceback

is_py3k = sys.version_info[0] > 2

is_winnt = os.name == "nt"
is_linux = os.name == "posix" and sys.platform.startswith("linux")
is_freebsd = os.name == "posix" and sys.platform.startswith("freebsd")
is_mac = os.name == "mac"
is_osx = os.name == "posix" and sys.platform == "darwin"
is_cygwin = os.name == "posix" and sys.platform == "cygwin"
is_mingw = is_winnt and os.environ.get('MSYSTEM', '').startswith('MINGW')
is_64bit = False
is_arm = False

if is_cygwin or is_mingw:
    print("ERROR: Cygwin or MingGW is not official support, please try to use Visual Studio 2010 Express or later.")
    sys.exit(-1)

import ez_setup
ez_setup.use_setuptools()

from distutils.command.build import build as _build
from setuptools import setup, Extension
from setuptools.command.develop import develop as _develop

# default settings, you can modify it in buildconf.py.
# please look in buildconf.py.example for more information
PYV8_HOME = os.path.abspath(os.path.dirname(__file__))
BOOST_HOME = None
BOOST_MT = is_osx
BOOST_STATIC_LINK = False
PYTHON_HOME = None
V8_HOME = None

INCLUDE = None
LIB = None
DEBUG = False

MAKE = 'gmake' if is_freebsd else 'make'

# load defaults from config file
try:
    from buildconf import *
except ImportError:
    pass

# override defaults from environment
PYV8_HOME = os.environ.get('PYV8_HOME', PYV8_HOME)
BOOST_HOME = os.environ.get('BOOST_HOME', BOOST_HOME)
BOOST_MT = os.environ.get('BOOST_MT', BOOST_MT)
PYTHON_HOME = os.environ.get('PYTHON_HOME', PYTHON_HOME)
V8_HOME = os.environ.get('V8_HOME', V8_HOME)
INCLUDE = os.environ.get('INCLUDE', INCLUDE)
LIB = os.environ.get('LIB', LIB)
DEBUG = os.environ.get('DEBUG', DEBUG)
MAKE = os.environ.get('MAKE', MAKE)

if isinstance(DEBUG, basestring):
    DEBUG = DEBUG.lower() in ['true', 'on', 't']

if V8_HOME is None or not os.path.exists(os.path.join(V8_HOME, 'include', 'v8.h')):
    print("WARN: V8_HOME doesn't exists or points to a wrong folder, ")
else:
    print("INFO: Found Google v8 base on V8_HOME <%s>" % V8_HOME)

source_files = ["Utils.cpp", "Exception.cpp", "Context.cpp", "Engine.cpp", "Wrapper.cpp",
                "Debug.cpp", "Locker.cpp", "AST.cpp", "PrettyPrinter.cpp", "PyV8.cpp"]

macros = [
    ("BOOST_PYTHON_STATIC_LIB", None),
]

boost_libs = ['boost_python', 'boost_thread', 'boost_system']

if BOOST_MT:
    boost_libs = [lib + '-mt' for lib in boost_libs]

if DEBUG:
    boost_libs = [lib + '-d' for lib in boost_libs]

include_dirs = [
    V8_HOME,
    os.path.join(V8_HOME, 'include'),
]
library_dirs = []
libraries = []
extra_compile_args = ['-std=c++11']
extra_link_args = ['-std=c++11']
extra_objects = []

if INCLUDE:
    include_dirs += [p for p in INCLUDE.split(os.path.pathsep) if p]
if LIB:
    library_dirs += [p for p in LIB.split(os.path.pathsep) if p]

if is_winnt:
    import platform
    is_64bit = platform.architecture()[0] == "64bit"

    include_dirs += [
        BOOST_HOME,
        os.path.join(PYTHON_HOME, 'include'),
    ]
    library_dirs += [
        os.path.join(BOOST_HOME, 'stage/lib'),
        os.path.join(BOOST_HOME, 'lib'),
        os.path.join(PYTHON_HOME, 'libs'),
    ]

    macros += [
        ("V8_TARGET_ARCH_X64" if is_64bit else "V8_TARGET_ARCH_IA32", None),
        ("WIN32", None),
    ]

    if not is_64bit:
        macros.append(("_USE_32BIT_TIME_T", None),)

    libraries += ["winmm", "ws2_32"]

    if DEBUG:
        extra_compile_args += ["/Od", "/MTd", "/EHsc", "/Gy", "/Zi"]
    else:
        extra_compile_args += ["/O2", "/GL", "/MT", "/EHsc", "/Gy", "/Zi"]

    extra_link_args += ["/DLL", "/OPT:REF", "/OPT:ICF", "/MACHINE:X64" if is_64bit else "/MACHINE:X86"]

    if DEBUG:
        extra_link_args += ["/DEBUG"]

    os.putenv('MSSdk', 'true')
    os.putenv('DISTUTILS_USE_SDK', 'true')
elif is_linux or is_freebsd:
    if BOOST_HOME:
        boost_lib_dir = os.path.join(BOOST_HOME, 'stage/lib')
        include_dirs += [BOOST_HOME]
    else:
        boost_lib_dir = '/usr/local/lib'
        include_dirs += ['/usr/local/include']

    library_dirs += [
        boost_lib_dir,
    ]

    if PYTHON_HOME:
        major, minor, _, _, _ = sys.version_info
        library_dirs += [os.path.join(PYTHON_HOME, 'lib/python%d.%d' % (major, minor))]
        include_dirs += [os.path.join(PYTHON_HOME, 'include')]

    extra_compile_args += ["-Wno-write-strings"]

    if BOOST_STATIC_LINK:
        extra_link_args += [os.path.join(boost_lib_dir, "lib%s.a") % lib for lib in boost_libs]
    else:
        libraries += boost_libs

    if is_freebsd:
        libraries += ["execinfo"]

    libraries += ["rt"]

    if hasattr(os, 'uname'):
        if os.uname()[-1] in ('x86_64', 'amd64'):
            is_64bit = True
            extra_link_args += ["-fPIC"]
        elif os.uname()[-1].startswith('arm'):
            is_arm = True
    else:
        macros += [("V8_TARGET_ARCH_IA32", None)]

#    if is_linux:
#        extra_link_args += ["-lrt"] # make ubuntu happy

    if DEBUG:
        extra_compile_args += ['-g', '-O0', '-fno-inline']
    else:
        extra_compile_args += ['-g', '-O3']

elif is_mac: # contribute by Artur Ventura
    include_dirs += [
        BOOST_HOME,
    ]
    library_dirs += [os.path.join('/lib')]
    libraries += boost_libs + ["c"]

elif is_osx: # contribute by progrium and alec
    # force x64 because Snow Leopard's native Python is 64-bit
    # scons arch=x64 library=static

    if BOOST_HOME:
        include_dirs += [BOOST_HOME]
        library_dirs += [os.path.join(BOOST_HOME, 'stage/lib'), os.path.join(BOOST_HOME, 'lib')]
    else:
        include_dirs += [
            "/opt/local/include", # MacPorts$ sudo port install boost
            "/usr/local/include", # HomeBrew$ brew install boost
        ]

        # MacPorts$ sudo port install boost
        if os.path.isdir("/opt/local/lib"):
            library_dirs.append("/opt/local/lib")

        # HomeBrew$ brew install boost
        if os.path.isdir("/usr/local/lib"):
            library_dirs.append("/usr/local/lib")

    libraries += boost_libs

    is_64bit = math.trunc(math.ceil(math.log(sys.maxsize, 2)) + 1) == 64 # contribute by viy

    if is_64bit:
        os.environ['ARCHFLAGS'] = '-arch x86_64'
        extra_link_args += ["-fPIC"]
    else:
        os.environ['ARCHFLAGS'] = '-arch i386'

    if DEBUG:
        extra_compile_args += ['-g', '-O0', '-fno-inline']
    else:
        extra_compile_args += ['-g', '-O3']

    extra_compile_args += ["-Wdeprecated-writable-strings", "-stdlib=libc++"]

else:
    print("ERROR: unsupported OS (%s) and platform (%s)" % (os.name, sys.platform))

arch = 'x64' if is_64bit else 'arm' if is_arm else 'ia32'
mode = 'debug' if DEBUG else 'release'


if is_winnt:
    library_path = icu_path = "%s/build/%s/lib/" % (V8_HOME, mode)

elif is_linux or is_freebsd:
    library_path = "%s/out.gn/%s.%s/obj/" % (V8_HOME, arch, mode)

elif is_osx:
    library_path = "%s/out.gn/%s.%s/obj/" % (V8_HOME, arch, mode)

library_dirs.append(library_path)


def exec_cmd(cmdline_or_args, msg, shell=True, cwd=V8_HOME, env=None, output=False):
    print("-" * 20)
    print("INFO: %s ..." % msg)
    print("DEBUG: > %s" % cmdline_or_args)

    proc = subprocess.Popen(cmdline_or_args, shell=shell, cwd=cwd, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    out, err = proc.communicate()

    succeeded = proc.returncode == 0

    if not succeeded:
        print("ERROR: %s failed: code=%d" % (msg or "Execute command", proc.returncode))
        print("DEBUG: %s" % err)

    return succeeded, out, err if output else succeeded

def generate_probes():
    build_path = os.path.join(PYV8_HOME, "build")

    if not os.path.exists(build_path):
        print("INFO: automatic make the build folder: %s" % build_path)

        try:
            os.makedirs(build_path, 0755)
        except os.error as ex:
            print("WARN: fail to create the build folder, %s" % ex)

    probes_d = os.path.join(PYV8_HOME, "src/probes.d")
    probes_h = os.path.join(PYV8_HOME, "src/probes.h")
    probes_o = os.path.join(build_path, "probes.o")

    if is_osx and exec_cmd("dtrace -h -xnolibs -s %s -o %s" % (probes_d, probes_h), "generate DTrace probes"):
        pass
    elif (is_linux or is_freebsd) and \
         (exec_cmd("dtrace -h -C -s %s -o %s" % (probes_d, probes_h), "generate DTrace probes.h") and \
          exec_cmd("dtrace -G -C -s %s -o %s" % (probes_d, probes_o), "generate DTrace probes.o")):
        extra_objects.append(probes_o)
    else:
        print("INFO: dtrace or systemtap doesn't works, force to disable probes")

        config_file = os.path.join(PYV8_HOME, "src/Config.h")

        with open(config_file, "r") as f:
            config_settings= f.read()

        modified_config_settings = config_settings.replace("\n#define SUPPORT_PROBES 1", "\n//#define SUPPORT_PROBES 1")

        if modified_config_settings != config_settings:
            if os.path.exists(config_file + '.bak'):
                os.remove(config_file + '.bak')

            os.rename(config_file, config_file + '.bak')

            with open(config_file, 'w') as f:
                f.write(modified_config_settings)

class build(_build):
    def run(self):
        _build.run(self)


class develop(_develop):
    def run(self):
        _develop.run(self)

print("%s - %s" % (str(libraries), str(library_dirs)))

pyv8 = Extension(name="_PyV8",
                 sources=[os.path.join("src", file) for file in source_files],
                 define_macros=macros,
                 include_dirs=include_dirs,
                 library_dirs=library_dirs,
                 libraries=libraries,
                 extra_compile_args=extra_compile_args,
                 extra_link_args=extra_link_args,
                 extra_objects=extra_objects,
                 )

extra = {}

if is_py3k:
    extra.update({
        'use_2to3': True
    })

classifiers = [
    'Development Status :: 4 - Beta',
    'Environment :: Plugins',
    'Intended Audience :: Developers',
    'Intended Audience :: System Administrators',
    'License :: OSI Approved :: Apache Software License',
    'Natural Language :: English',
    'Operating System :: Microsoft :: Windows',
    'Operating System :: POSIX',
    'Programming Language :: C++',
    'Programming Language :: Python',
    'Programming Language :: Python :: 3',
    'Topic :: Internet',
    'Topic :: Internet :: WWW/HTTP',
    'Topic :: Software Development',
    'Topic :: Software Development :: Libraries :: Python Modules',
    'Topic :: Utilities',
    ]

description = """
PyV8 is a python wrapper for Google V8 engine, it act as a bridge
between the Python and JavaScript objects, and support to hosting
Google's v8 engine in a python script.
"""

setup(name='PyV8',
      cmdclass = { 'build': build, 'v8build': _build, 'develop': develop },
      version='1.0-dev',
      description='Python Wrapper for Google V8 Engine',
      long_description=description,
      platforms="x86",
      author='Flier Lu',
      author_email='flier.lu@gmail.com',
      url='svn+http://pyv8.googlecode.com/svn/trunk/#egg=pyv8-1.0-dev',
      download_url='http://code.google.com/p/pyv8/downloads/list',
      license="Apache Software License",
      install_requires=['setuptools'],
      py_modules=['PyV8'],
      ext_modules=[pyv8],
      test_suite='PyV8',
      classifiers=classifiers,
      **extra)
