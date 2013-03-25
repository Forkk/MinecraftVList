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

from datetime import datetime

import re

# This pattern matches all the characters allowed in an MD5, but doesn't check the length. That should be done separately.
md5pattern = re.compile(r'^[a-fA-F0-9]+$')

def validate_md5(md5):
	"""Checks whether or not the given string is a valid md5sum."""
	return True if len(md5) == 32 and md5pattern.search(md5) else False

def datetime_from_s3(s3time):
	"""Converts an Amazon S3 timestamp into a datetime object."""
	return datetime.strptime(s3time, "%Y-%m-%dT%H:%M:%S.000Z")

def s3time_from_datetime(dtime):
	"""Converts a datetime object into an Amazon S3 timestamp."""
	return datetime.strftime(dtime, "%Y-%m-%dT%H:%M:%S.000Z")
