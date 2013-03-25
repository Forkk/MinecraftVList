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
