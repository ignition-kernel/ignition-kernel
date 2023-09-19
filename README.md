# ignition-kernel
Aegis repo for tracking the code to connect Ignition into Jupyter.

# Structure

Since Ignition manages the kernel on its own, there will be two main projects:
* a Jupyter kernel project to add to Ignition
* a Jupyter provisioner that interacts with Ignition

Provisioner requires at least Python 3.6.1 as per `jupyter-client` >=v7.0.0.

For sanity's sake, the version of the Ignition project and the kernel provisioner are kept in lockstep.
