Ignition project exports and imports are processed here.

Place project export zips in `./dist/` - and make sure to put it's version in the name.

Unpack will take the largest version and replace `./python` and `./webdev` with their contents.

Pack will do the opposite, placing those two folders into a zip, packed in the needed locations
and signed with their resource.json files.