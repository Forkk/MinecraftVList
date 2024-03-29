# Copyright 2013 Andrew Okin
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import json

import versionmodel as vm

def main():
	vlist = list()

	cached_versions = vm.VersionModel.select()

	for ver in cached_versions:
		obj = { "name": ver.version_name, "suburl": ver.suburl, "etag": ver.etag, "md5sum": ver.md5sum, "vtype": ver.version_type, "timestamp": ver.timestamp }
		vlist.append(obj)

	print json.dumps({ "vlist": vlist })


if __name__ == "__main__":
	main()
