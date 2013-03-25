from peewee import *

import versionlist as vl

version_db = MySQLDatabase("mmcvlist", host = "127.0.0.1", port=3306, user = "mmcvlist")
connected = False

def from_instlist_version(v):
		"""Creates a VersionModel from the given Version."""
		return VersionModel.create(version_name = v.name, suburl = v.suburl, etag = v.etag, md5sum = v.md5sum, version_type = v.vtype, timestamp = v.timestamp)

class VListDBModel(Model):
	class Meta:
		database = version_db

class VersionModel(VListDBModel):
	"""A class for storing Versions in a database using peewee"""

	version_name = TextField()
	suburl = CharField(primary_key = True, max_length = 256)
	etag = TextField()
	md5sum = TextField(null = True)
	version_type = TextField(null = True)
	timestamp = IntegerField()

	def to_instlist_version(self):
		return vl.Version(
			name = self.version_name,
			suburl = self.suburl, 
			etag = self.etag,
			md5sum = self.md5sum,
			vtype = self.version_type,
			timestamp = self.timestamp)

	def update_from_instlist_version(self, v, autosave_if_changed = True):
		"""Updates this model from the given version."""

		should_save = False
		if (autosave_if_changed and
				self.version_name != v.name or
				self.suburl != v.suburl or
				self.etag != v.etag or
				self.md5sum != v.md5sum or
				self.version_type != v.vtype or
				self.timestamp != v.timestamp):
			should_save = True

		self.version_name = v.name
		self.suburl = v.suburl
		self.etag = v.etag
		self.md5sum = v.md5sum
		self.version_type = v.vtype
		self.timestamp = v.timestamp

		if should_save:
			print "Updated version %s in database." % self.version_name
			self.save()
