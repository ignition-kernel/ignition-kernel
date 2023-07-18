# ignition-kernel
Aegis repo for tracking the code to connect Ignition into Jupyter.

# Structure

Since Ignition manages the kernel on its own, there will be two main projects:
* a Jupyter kernel project to add to Ignition
* a Jupyter provisioner that interacts with Ignition

Provisioner requires at least Python 3.6.1 as per `jupyter-client` >=v7.0.0.

For sanity's sake, the version of the Ignition project and the kernel provisioner are kept in lockstep.


# Quickstart

`pip install ignition_jupyter_kernel --upgrade`

For a blank, fresh install gateway:
`python -m ignition_kernel --install`

I have a cert just to stay in the habit of using HTTPS, so my setup looks like this:

```sh
c:\Workspace>python -m ignition_kernel --install --hostname https://localhost.corso.systems:8043

Adding the following kernel:
Config                         Value
------------------------------ -----
Name                           Ignition-CS-Surface61
Gateway Homepage               https://localhost.corso.systems:8043
WebDev Endpoint                system/webdev/jupyter/kernel
Auth username                  admin
Password in Keyring            False
Enter the password for the user 'admin' :
Password saved in Keyring for admin@https://localhost.corso.systems:8043

c:\Workspace>
```
