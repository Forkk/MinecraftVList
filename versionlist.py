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

from xml.etree import ElementTree

from collections import Counter

from io import BytesIO
from tempfile import SpooledTemporaryFile
from zipfile import ZipFile
import hashlib

from datetime import datetime
import calendar
import urllib2
import re

import peewee
import versionmodel as vm

import util

assets_url = "http://assets.minecraft.net/"
mcdl_url = "http://s3.amazonaws.com/MinecraftDownload/"

class Version:
	"""Represents a version of Minecraft."""

	name = ""
	suburl = ""
	etag = ""
	md5sum = ""
	vtype = ""
	timestamp = 0

	def __init__(self, name = "", suburl = "", timestamp = 0, etag = "", md5sum = None, vtype = None):
		self.name = name
		self.suburl = suburl
		self.etag = etag
		self.vtype = vtype
		self.timestamp = timestamp


	def should_update_md5(self):
		return not util.validate_md5(self.md5sum)


	def update_md5(self, url = assets_url):
		"""Updates the version's md5sum. If the version's ETag is a valid MD5, then this simply sets md5sum to the ETag. If the ETag is not an md5sum, calls calculate_md5()."""

		# Check the ETag to see if it's a valid MD5
		if util.validate_md5(self.etag):
			# If the ETag is a valid MD5, then set md5sum to the ETag.
			self.md5sum = self.etag

		else:
			# If the ETag isn't a valid MD5, try getting one from the cache. If that fails, we need to calculate it ourselves.
			if not self.load_cached_md5():
				self.calculate_md5(url)

	def calculate_md5(self, url = assets_url, download_times = 3, dl_tries = 3):
		"""Calculates the version's MD5 manually. This is done by downloading the file repeatedly (how many times this is done can be specified via the download_times argument), and calculating the MD5 of each file downloaded, keeping track of each MD5. If dl_tries is greater than 0, each file is also checked to make sure it's a valid zip file and discarded if not to help ensure validity. If this fails more than tries times, the function assumes the file to be valid and carries on."""

		print "Calculating MD5 for version %s" % self.name

		import random
		import os

		md5sums = []
		
		dl_url = url + self.suburl + "/minecraft.jar"
		for dl_count in range(download_times):
			md5str = None
			try_count = 0
			while not md5str:
				try_count += 1
				if dl_tries > 0 and try_count > dl_tries:
					break

				print "Download #%i, try #%i from %s" % (dl_count+1, try_count, dl_url)

				response = urllib2.urlopen(dl_url)
				with SpooledTemporaryFile(max_size = (1024**2)*24) as data: # Limit the SpooledTemporaryFile to 24c MB
					data.write(response.read())
					data.flush()

					# Find the length of the file.
					data.seek(0, 2)
					filelen = data.tell()

					# Randomly corrupt the file (for SCIENCE!)
					# data.seek(random.randint(0, filelen)); data.write(os.urandom(1024))

					data.seek(0) # Seek to the beginning.

					if (dl_tries > 0):
						# Verify that the file is a zip file and if not, retry.
						result = None
						try:
							with ZipFile(data) as zipfile:
								result = zipfile.testzip()
						except:
							result = -1

						if result is not None:
							if try_count < dl_tries:
								print "%s was not a valid zip file. Retrying." % self.name
								continue
							else:
								print "%s was not a valid zip file. Tried too many times, Getting MD5 anyways..." % self.name

					# Get the file's MD5.
					data.seek(0)
					md5 = hashlib.md5()
					md5.update(data.read())
					md5str = md5.hexdigest()
					md5sums.append(md5str)
					print "MD5 of download #%i: %s" % (dl_count, md5str)

		# Count md5sums
		ctr = Counter(md5sums)
		counts = ctr.most_common(1)
		print "\tMost common MD5 (received %i times): %s ETag: %s" % (counts[0][1], counts[0][0], self.etag)
		self.md5sum = counts[0][0]


	def load_cached_md5(self):
		"""Checks the database for this version's previously cached MD5 and loads it if the ETags match. Returns True if a cached value was loaded."""

		if not vm.VersionModel.table_exists():
			print "No cache table found."
			return False

		try:
			# Find the cached data for this version.
			cached = vm.VersionModel.get(vm.VersionModel.suburl == self.suburl)

			# Check if the ETags match and if so, load the cached MD5.
			if util.validate_md5(cached.md5sum) and self.etag == cached.etag:
				print "Loaded cached MD5 %s for version %s." % (cached.md5sum, self.name)
				self.md5sum = cached.md5sum
				return True
			else:
				print "Not loading cached MD5 for version %s: ETag mismatch or null MD5." % self.name
				return False

		except vm.VersionModel.DoesNotExist:
			print "No cached data found for version %s" % self.name
			return False


	def __str__(self, verbose = False):
		if not verbose:
			return self.name
		else:
			return "Version %(name)s:\n\
\tType: %(vtype)s\n\
\tSub-URL: %(suburl)s\n\
\tETag: %(etag)s\n\
\tMD5sum: %(checksum)s \n\
\tTimestamp: %(timestamp)i\
					" % dict(name = self.name, vtype = self.vtype, suburl = self.suburl, etag = self.etag, checksum = self.md5sum, timestamp = self.timestamp)



class VersionList:
	def __init__(self):
		self.versions = list()
		self.cvinfo = None


	def load_from_assets(self, url = assets_url):
		"""Loads information from assets.minecraft.net into the version list."""

		if not self.cvinfo and not self.load_current_version_info():
			print "Failed loading current version."
			return False # Fail if we haven't loaded the current version info before, and trying to load it fails.

		# Load a list of versions.
		templist = self.load_from_s3index(url)

		self.versions = templist


	def load_current_version_info(self, url = mcdl_url):
		"""Loads information about the current version of Minecraft. (The version found s3.amazonaws.com/MinecraftDownload)"""

		# Load a list from the main download (there should only be one version in this list).
		templist = self.load_from_s3index(url, r"^minecraft\.jar$")

		# If the length is less than one, or the first item is None, fail.
		if len(templist) < 1 or not templist[0]:
			print "Failed to find current version info."
			return False

		self.cvinfo = templist[0]
		return True


	def load_from_s3index(self, url, key_regex = r"/minecraft\.jar$"):
		"""Loads a list of versions from a URL."""
		tlist = list()

		regex = re.compile(key_regex)

		response = urllib2.urlopen(url)
		xmlstr = response.read()

		root = ElementTree.fromstring(xmlstr)
		xmlns = root.tag[root.tag.find("{") : root.tag.find("}")+1] # I

		for item in root.findall(xmlns + "Contents"): # Hate

			key = item.findtext(xmlns + "Key", "") # XML

			if not regex.search(key):
				continue	

			suburl = key[:-14] # But I love Python...
			vname = suburl.replace("_", ".")
			timestamp = calendar.timegm(util.datetime_from_s3(item.findtext(xmlns + "LastModified", util.s3time_from_datetime(datetime.now()))).timetuple()) # I don't even...
			etag = item.findtext(xmlns + "ETag").strip('"') # Strip quotes from ETag. Seriously, why the hell are they even there?

			ver = Version(name = vname, suburl = suburl, timestamp = timestamp, etag = etag)
			tlist.append(ver)

		return tlist


	def update_md5s(self, url = assets_url):
		"""Goes through each item in the version list and checks if its md5sum is valid. If not, calls retrieve_md5 on that version. See Version.update_md5 for more info."""

		for ver in self.versions:
			if ver.should_update_md5():
				ver.update_md5()


	def update_version_types(self):
		"""Goes through each version and determines its type."""

		snapshot_regex = re.compile(r"^[0-9][0-9]w[0-9][0-9][a-z]|pre|rc2?$")

		for ver in self.versions:
			if ver.md5sum == self.cvinfo.etag:
				ver.vtype = "CurrentStable" # We found the current stable version!
				continue

			older = ver.timestamp < self.cvinfo.timestamp
			newer = ver.timestamp > self.cvinfo.timestamp
			is_snapshot = snapshot_regex.search(ver.name)

			if is_snapshot:
				if newer:
					ver.vtype = "Snapshot"
				else:
					ver.vtype = "OldSnapshot"
			else:
				ver.vtype = "Stable"


	def save_to_db(self):
		if not vm.VersionModel.table_exists():
			vm.VersionModel.create_table()

		for ver in self.versions:
			try:
				vmodel = vm.VersionModel.select().where(vm.VersionModel.suburl == ver.suburl).get()
				print "Updating previously cached version: %s" % vmodel.version_name
				vmodel.update_from_instlist_version(ver)

			except vm.VersionModel.DoesNotExist:
				print "Adding new version: %s" % ver.name
				vmodel = vm.from_instlist_version(ver)


	def load_cached_info(self):
		"""Loads and returns a list of versions that were cached."""
		
		if not vm.VersionModel.table_exists():
			print "No cache found."
			return list()

		else:
			print "Loading cache..."
			cached_versions = vm.VersionModel.select() # Select all from the table.

			cache_vlist = list()

			for vmodel in cached_versions:
				ver = vmodel.to_instlist_version()			
				print "Loaded version %s from cache." % ver
				cache_vlist.append(ver)

			return cache_vlist


def main():
	vlist = VersionList()

	# Load from assets.
	vlist.load_from_assets()

	# Load the MD5sums
	vlist.update_md5s()

	# Get the types of each version.
	vlist.update_version_types()

	# Save to the database.
	vlist.save_to_db()

if __name__ == "__main__":
	main()
