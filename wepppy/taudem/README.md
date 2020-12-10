# wepppy-taudem-topazemu

## Installation

Requires MPICH2 for proper operation. Other versions of MPI (OpenMPI) may run but provide different results.

On linux

```
> sudo apt install mpich
```

Check the version with:

```
> mpiexec --version
HYDRA build details:
    Version:                                 3.3a2
    Release Date:                            Sun Nov 13 09:12:11 MST 2016
    CC:                              gcc   -Wl,-Bsymbolic-functions -Wl,-z,relro
    CXX:                             g++   -Wl,-Bsymbolic-functions -Wl,-z,relro
    F77:                             gfortran  -Wl,-Bsymbolic-functions -Wl,-z,relro
    F90:                             gfortran  -Wl,-Bsymbolic-functions -Wl,-z,relro
    Configure options:                       '--disable-option-checking' '--prefix=/usr' '--build=x86_64-linux-gnu' '--includedir=${prefix}/include' '--mandir=${prefix}/share/man' '--infodir=${prefix}/share/info' '--sysconfdir=/etc' '--localstatedir=/var' '--disable-silent-rules' '--libdir=${prefix}/lib/x86_64-linux-gnu' '--libexecdir=${prefix}/lib/x86_64-linux-gnu' '--disable-maintainer-mode' '--disable-dependency-tracking' '--with-libfabric' '--enable-shared' '--enable-fortran=all' '--disable-rpath' '--disable-wrapper-rpath' '--sysconfdir=/etc/mpich' '--libdir=/usr/lib/x86_64-linux-gnu' '--includedir=/usr/include/mpich' '--docdir=/usr/share/doc/mpich' '--with-hwloc-prefix=system' '--enable-checkpointing' '--with-hydra-ckpointlib=blcr' 'CPPFLAGS= -Wdate-time -D_FORTIFY_SOURCE=2 -I/build/mpich-O9at2o/mpich-3.3~a2/src/mpl/include -I/build/mpich-O9at2o/mpich-3.3~a2/src/mpl/include -I/build/mpich-O9at2o/mpich-3.3~a2/src/openpa/src -I/build/mpich-O9at2o/mpich-3.3~a2/src/openpa/src -D_REENTRANT -I/build/mpich-O9at2o/mpich-3.3~a2/src/mpi/romio/include' 'CFLAGS= -g -O2 -fdebug-prefix-map=/build/mpich-O9at2o/mpich-3.3~a2=. -fstack-protector-strong -Wformat -Werror=format-security -O2' 'CXXFLAGS= -g -O2 -fdebug-prefix-map=/build/mpich-O9at2o/mpich-3.3~a2=. -fstack-protector-strong -Wformat -Werror=format-security -O2' 'FFLAGS= -g -O2 -fdebug-prefix-map=/build/mpich-O9at2o/mpich-3.3~a2=. -fstack-protector-strong -O2' 'FCFLAGS= -g -O2 -fdebug-prefix-map=/build/mpich-O9at2o/mpich-3.3~a2=. -fstack-protector-strong -O2' 'build_alias=x86_64-linux-gnu' 'MPICHLIB_CFLAGS=-g -O2 -fdebug-prefix-map=/build/mpich-O9at2o/mpich-3.3~a2=. -fstack-protector-strong -Wformat -Werror=format-security' 'MPICHLIB_CPPFLAGS=-Wdate-time -D_FORTIFY_SOURCE=2' 'MPICHLIB_CXXFLAGS=-g -O2 -fdebug-prefix-map=/build/mpich-O9at2o/mpich-3.3~a2=. -fstack-protector-strong -Wformat -Werror=format-security' 'MPICHLIB_FFLAGS=-g -O2 -fdebug-prefix-map=/build/mpich-O9at2o/mpich-3.3~a2=. -fstack-protector-strong' 'MPICHLIB_FCFLAGS=-g -O2 -fdebug-prefix-map=/build/mpich-O9at2o/mpich-3.3~a2=. -fstack-protector-strong' 'LDFLAGS=-Wl,-Bsymbolic-functions -Wl,-z,relro' 'FC=gfortran' 'F77=gfortran' 'MPILIBNAME=mpich' '--cache-file=/dev/null' '--srcdir=.' 'CC=gcc' 'LIBS=' 'MPLLIBNAME=mpl'
    Process Manager:                         pmi
    Launchers available:                     ssh rsh fork slurm ll lsf sge manual persist
    Topology libraries available:            hwloc
    Resource management kernels available:   user slurm ll lsf sge pbs cobalt
    Checkpointing libraries available:       blcr
    Demux engines available:                 poll select
```

If it is OpenMPI or Intel then change /usr/bin/mpiexec symlink

```
> sudo rm /usr/bin/mpiexec
> ln -s /usr/bin/mpiexec.hydra /usr/bin/mpiexec
```
