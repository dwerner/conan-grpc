from conans import ConanFile, CMake, tools
import os
import shutil

class gRPCConan(ConanFile):
    name = "gRPC"
    version = "1.10.0"
    folder = "grpc-%s" % version
    description = "Google's RPC library and framework."
    url = "https://github.com/inexorgame/conan-grpc.git"
    license = "Apache-2.0"
    requires = "zlib/1.2.11@conan/stable", "OpenSSL/1.1.0g@conan/stable", "protobuf/3.5.1@bincrafters/stable", "gflags/2.2.1@bincrafters/stable", "c-ares/1.14.0@conan/stable" , "benchmark/1.3.0@bincrafters/testing"
    settings = "os", "compiler", "build_type", "arch"
    options = {
            "shared": [True, False],
            "enable_mobile": [True, False],  # Enables iOS and Android support
            "non_cpp_plugins":[True, False]  # Enables plugins such as --java-out and --py-out (if False, only --cpp-out is possible)
            }
    default_options = '''shared=False
    enable_mobile=False
    non_cpp_plugins=False
    '''
    generators = "cmake"
    short_paths = True  # Otherwise some folders go out of the 260 chars path length scope rapidly (on windows)

    def source(self):
        #tools.download("https://github.com/grpc/grpc/archive/v{}.zip".format(self.version), "grpc.zip")
        #tools.unzip("grpc.zip")
        #os.unlink("grpc.zip")
        self.run("git clone -b v{} --single-branch --recursive --depth 1 https://github.com/grpc/grpc.git grpc-{}".format(self.version, self.version))
        # --shallow-submodules doesn't work, unadvertised objects, would bring down the download/file size dramatically
        # self.run("git submodule update --init");
        cmake_name = "{}/CMakeLists.txt".format(self.folder)

        # tell grpc to use our deps and flags
        tools.replace_in_file(cmake_name, "project(${PACKAGE_NAME} C CXX)", '''project(${PACKAGE_NAME} C CXX)
        include(${CMAKE_BINARY_DIR}/conanbuildinfo.cmake)
        conan_basic_setup()''')

        tools.replace_in_file(cmake_name, "set(gRPC_ZLIB_PROVIDER \"module\"", '''set(gRPC_ZLIB_PROVIDER \"package\"''')
        tools.replace_in_file(cmake_name, "set(gRPC_SSL_PROVIDER \"module\"", '''set(gRPC_SSL_PROVIDER \"package\"''')
        tools.replace_in_file(cmake_name, "set(gRPC_PROTOBUF_PROVIDER \"module\"", '''set(gRPC_PROTOBUF_PROVIDER \"package\"''')
        tools.replace_in_file(cmake_name, "set(gRPC_GFLAGS_PROVIDER \"module\"", '''set(gRPC_GFLAGS_PROVIDER \"package\"''')
        tools.replace_in_file(cmake_name, "set(gRPC_BENCHMARK_PROVIDER \"module\"", '''set(gRPC_BENCHMARK_PROVIDER \"package\"''')

        tools.replace_in_file(cmake_name, "set(gRPC_CARES_PROVIDER \"module\"", '''set(gRPC_CARES_PROVIDER \"package\"''')

        # skip installing the headers, TODO: use these!
        # gRPC > 1.6 changes the CMAKE_INSTALL_INCLUDEDIR vars to gRPC_INSTALL_INCLUDEDIR !!
        tools.replace_in_file(cmake_name, '''  install(FILES ${_hdr}
    DESTINATION "${gRPC_INSTALL_INCLUDEDIR}/${_path}"
  )''', '''  # install(FILES ${_hdr} # COMMENTED BY CONAN
    # DESTINATION "${gRPC_INSTALL_INCLUDEDIR}/${_path}"
  # )''')

        # Add some CMake Variables (effectively commenting out stuff we do not support)
        tools.replace_in_file(cmake_name, "add_library(grpc_cronet", '''if(CONAN_ENABLE_MOBILE)
        add_library(grpc_cronet''')
        tools.replace_in_file(cmake_name, "add_library(grpc_unsecure", '''endif(CONAN_ENABLE_MOBILE)
        add_library(grpc_unsecure''')
        tools.replace_in_file(cmake_name, "add_library(grpc++_cronet", '''if(CONAN_ENABLE_MOBILE)
        add_library(grpc++_cronet''')
        tools.replace_in_file(cmake_name, "add_library(grpc++_reflection", '''endif(CONAN_ENABLE_MOBILE)
        if(CONAN_ENABLE_REFLECTION_LIBS)
        add_library(grpc++_reflection''')
        tools.replace_in_file(cmake_name, "add_library(grpc++_unsecure", '''endif(CONAN_ENABLE_REFLECTION_LIBS)
        add_library(grpc++_unsecure''')
        tools.replace_in_file(cmake_name, "add_executable(grpc_csharp_plugin", '''if(CONAN_ADDITIONAL_PLUGINS)
        add_executable(grpc_csharp_plugin''')
        # gRPC > 1.6 changes the CMAKE_INSTALL_BINDIR vars to gRPC_INSTALL_BINDIR !!
        tools.replace_in_file(cmake_name, '''install(TARGETS grpc_ruby_plugin EXPORT gRPCTargets
    RUNTIME DESTINATION ${gRPC_INSTALL_BINDIR}
    LIBRARY DESTINATION ${gRPC_INSTALL_LIBDIR}
    ARCHIVE DESTINATION ${gRPC_INSTALL_LIBDIR}
  )
endif()''', '''install(TARGETS grpc_ruby_plugin EXPORT gRPCTargets
    RUNTIME DESTINATION ${gRPC_INSTALL_BINDIR}
    LIBRARY DESTINATION ${gRPC_INSTALL_BINDIR}
    ARCHIVE DESTINATION ${gRPC_INSTALL_BINDIR}
  )
endif()
endif(CONAN_ADDITIONAL_PLUGINS)''')

    def build(self):
        tmp_install_dir = "{}/install".format(self.build_folder)

        if not os.path.exists(tmp_install_dir):
            os.mkdir(tmp_install_dir)

        args = [
                "-DgRPC_INSTALL=ON", 
                "-DgRPC_CARES_PROVIDER=package",
                "-DgRPC_ZLIB_PROVIDER=package",
                "-DgRPC_SSL_PROVIDER=package",
                "-DgRPC_PROTOBUF_PROVIDER=package",
                "-DgRPC_GFLAGS_PROVIDER=package",
                "-DgRPC_BENCHMARK_PROVIDER=package",
                '-DCMAKE_INSTALL_PREFIX="{}"'.format(tmp_install_dir)
                ] # We need the generated cmake/ files (bc they depend on the list of targets, which is dynamic)
        if self.options.non_cpp_plugins:
            args += ["-DCONAN_ADDITIONAL_PLUGINS=ON"]
        if self.options.enable_mobile:
            args += ["-DCONAN_ENABLE_MOBILE=ON"]
        cmake = CMake(self)
        self.run('cmake {0}/{1} {2} {3}'.format(self.source_folder, self.folder, cmake.command_line, ' '.join(args)))
        self.run("cmake --build . --target install {}".format(cmake.build_config))

    def package(self):
        cmake_files = ["gRPCConfig.cmake", "gRPCConfigVersion.cmake", "gRPCTargets.cmake"]
        install_lib_path = self.get_install_lib_path()
        cmake_folder = "{}/cmake/grpc".format(install_lib_path)

        print("cmake folder " + cmake_folder) 

        for file in cmake_files:
            self.copy(file, dst='.', src=cmake_folder)
        # Copy the build_type specific file only for our used one:
        self.copy(
                "gRPCTargets-{}.cmake".format("debug" if self.settings.build_type == "Debug" else "release"),
                dst=".", 
                src=cmake_folder
         )

        self.copy('*', dst='include', src='{}/include'.format(self.folder))
        self.copy("*.lib", dst="lib", src="", keep_path=False)
        self.copy("*.a", dst="lib", src="", keep_path=False)
        self.copy("*", dst="bin", src="bin")
        self.copy("*.dll", dst="bin", keep_path=False)
        self.copy("*.so", dst="lib", keep_path=False)

    def package_info(self):
        self.cpp_info.libs = ["grpc", "grpc++", "grpc_unsecure", "grpc++_unsecure", "gpr"]
        if self.settings.compiler == "Visual Studio":
            self.cpp_info.libs += ["wsock32", "ws2_32"]

    def get_install_lib_path(self):
        install_path = "{}/install".format(self.build_folder)
        target_cmake = "{}/lib/cmake/grpc/gRPCTargets.cmake".format(install_path)
        target64_cmake = "{}/lib64/cmake/grpc/gRPCTargets.cmake".format(install_path)
        if os.path.isfile(target_cmake):
            print("target_cmake: " + target_cmake)
            return "{}/lib".format(install_path)
        elif os.path.isfile(target64_cmake):
            return "{}/lib64".format(install_path)
        return "UNKNOWN"
