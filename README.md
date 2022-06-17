# ignition-kernel
Aegis repo for tracking the tweaks and backports to make the IPython Kernel work Ignition for Jupyter

# Structure

Submodule forks are used in case tweaks and patches are needed. Each will operate in a branch called `ignition-kernel`.

##Tooling

Helper processes in generating and maintaining the library.

### `lib3to6`
Automagically convert newer modules to Python 2.7 compatible code. This is needed to both make sure coverage is good and to test that the libraries are converted correctly.

## `pylib`

Ignition will need these libraries to work `ipykernel`.

### `traitlets`


