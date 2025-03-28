#!/usr/bin/env python3
#
# Copyright 2015 The Chromium Authors.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Updates the CREDITS.chromium file for ffmpeg.

The structure of the output credits file is:
- FFmpeg LICENSE.md verbatim
- A few verbatim license headers from files that didn't match typical FFmpeg
- The entire text of the LGPL

The vast majority of files are covered by the LGPL text, described by the
common FFmpeg header ("This file is part of FFmpeg...").

The few exceptions are cases where the FFmpeg header has been modified, or
where the file has historically had another license (e.g MIPS, JPEG, BSD) and
was pulled into FFmpeg from another project. In some cases there are many files
that share the exact same non-LGPL license text. These are bucketed together
(see KNOWN_FILE_BUCKETS) to de-dup their license in the output file.

Change to the licensing text for bucketed files are automatically caught by
comparing the md5 digest to a previously recorded digest in the
KNOWN_FILE_BUCKETS table. Changes are generally not expected, but should
prompt manual inspection of the difference and possibly an update to the
license text for that bucket.
"""

__author__ = 'chcunningham@chromium.org (Chris Cunningham)'

import collections
import difflib
import hashlib
import os
import re

# Name of the LICENSE.md file from upstream FFmpeg. This file should be kept in
# perfect sync w/ upstream at each merge.
UPSTREAM_LICENSEMD = 'LICENSE.md'

# Default name of the output file generated by CreditsUpdater.WriteCredits. This
# name must match the "License file: " in README.chromium.
DEFAULT_OUTPUT_FILE = 'CREDITS.chromium'

# Minimum similarity threshold to consider a comment header LGPL when compared
# against FFMPEG_LGPL_REF.
LGPL_MATCH_THRESHOLD = .9

# Regular expressions for finding license header comments.
C_COMMENT_BLOCK_START = re.compile('/\*+')
C_COMMENT_BLOCK_MID = re.compile('^ *\* *')
C_COMMENT_BLOCK_END = re.compile('\*/')
ASM_COMMENT_PRE = re.compile('^(;\**|@)')
ASM_NOT_COMMENT = re.compile('^[^;@]')
FFMPEG_HEADER_START = re.compile(' *This file is part of FFmpeg')

LICENSE_SEPARATOR = '\n\n' + ('*' * 80) + '\n\n'
FFMPEG_LGPL_REF = """
 * This file is part of FFmpeg.
 *
 * FFmpeg is free software; you can redistribute it and/or
 * modify it under the terms of the GNU Lesser General Public
 * License as published by the Free Software Foundation; either
 * version 2.1 of the License, or (at your option) any later version.
 *
 * FFmpeg is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
 * Lesser General Public License for more details.
 *
 * You should have received a copy of the GNU Lesser General Public
 * License along with FFmpeg; if not, write to the Free Software
 * Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA
 */"""

# Known licenses
_Licenses = ('LGPL', 'MIPS', 'JPEG', 'OGG_MA_MR_2005')
License = collections.namedtuple('License', _Licenses)(*_Licenses)

# Tuple describing license and similarity to the FFmpeg LGPL reference for a
# given file. See KNOWN_FILE_BUCKETS.
FileInfo = collections.namedtuple('FileInfo', 'license, license_digest')

# Most files in FFmpeg are LGPL, but there are a few exceptions that are worth
# bucketing together to avoid redundant license texts. The hex values are
# digests of the comment header, used to detect changes in the unlikely event
# that their license texts are altered. Any changes will require manual review
# to decide whether the to update the bucketing.
KNOWN_FILE_BUCKETS = [
    # Files that are LGPL but just miss the similarity cutoff.
    [
        'libavcodec/codec_desc.c', License.LGPL,
        '091f9c6d1efc62038e516f5c67263962'
    ],
    # Files with MIPS license.
    [
        'libavcodec/mdct_fixed_32.c', License.MIPS,
        '179c17c9dab77f95dc6540709b5fb8cd'
    ],
    [
        'libavcodec/fft_fixed_32.c', License.MIPS,
        '179c17c9dab77f95dc6540709b5fb8cd'
    ],
    [
        'libavcodec/fft_init_table.c', License.MIPS,
        '179c17c9dab77f95dc6540709b5fb8cd'
    ],
    [
        'libavcodec/mips/aacdec_mips.c', License.MIPS,
        'a08afe43d908fe6625603d0cbc95da46'
    ],
    [
        'libavcodec/mips/sbrdsp_mips.c', License.MIPS,
        'c34ece06ebe27e5a7611ef362962b048'
    ],
    [
        'libavcodec/mips/aacpsdsp_mips.c', License.MIPS,
        'a08afe43d908fe6625603d0cbc95da46'
    ],
    [
        'libavutil/mips/float_dsp_mips.c', License.MIPS,
        'fb9f51968ec8289768547144b920cf79'
    ],
    [
        'libavcodec/mips/aacsbr_mips.c', License.MIPS,
        '82c53533b2576fe5d2c04880a46595f2'
    ],
    [
        'libavutil/fixed_dsp.c', License.MIPS,
        '7a521412ac91287b3e1026885f6bd56f'
    ],
    [
        'libavcodec/mips/aacdec_mips.h', License.MIPS,
        'c34ece06ebe27e5a7611ef362962b048'
    ],
    [
        'libavcodec/mips/lsp_mips.h', License.MIPS,
        'eef419f576f738e66ca3bfc975a37996'
    ],
    [
        'libavcodec/mips/aacsbr_mips.h', License.MIPS,
        '82c53533b2576fe5d2c04880a46595f2'
    ],
    [
        'libavutil/mips/libm_mips.h', License.MIPS,
        '4b408982f2aa83fac9c020c61853bdae'
    ],
    [
        'libavcodec/mips/amrwbdec_mips.h', License.MIPS,
        '4b408982f2aa83fac9c020c61853bdae'
    ],
    [
        'libavcodec/fft_table.h', License.MIPS,
        '179c17c9dab77f95dc6540709b5fb8cd'
    ],
    [
        'libavcodec/mips/compute_antialias_float.h', License.MIPS,
        'a7ff7e3157e3726cba79e022628d3b93'
    ],
    [
        'libavcodec/mips/compute_antialias_fixed.h', License.MIPS,
        '97e366b4c71ad5ceca991d89044c414d'
    ],
    [
        'libavutil/softfloat_tables.h', License.MIPS,
        'de3e5c962caa5c8249bef3085ef36bc8'
    ],
    [
        'libavutil/fixed_dsp.h', License.MIPS,
        '4b408982f2aa83fac9c020c61853bdae'
    ],
    # Files with JPEG Group license.
    [
        'libavcodec/jfdctint_template.c', License.JPEG,
        'd80cfd2e439eb700aed0f5bc44fef9b5'
    ],
    [
        'libavcodec/jfdctfst.c', License.JPEG,
        '7dcfa68ad9c8fd940fb404ee3242e03f'
    ],
    ['libavcodec/jrevdct.c', License.JPEG, 'a9b8f5dcb74fa76a72069306b841b042'],
    # Files written by Ahlberg and RullgAYrd for parsing Ogg (MIT/X11 license).
    [
        'libavformat/oggparseogm.c', License.OGG_MA_MR_2005,
        'ee65196bafec5d8e871e64bb739bdc79'
    ],
    [
        'libavformat/oggdec.c', License.OGG_MA_MR_2005,
        '43ed5da1268cb2f104095c79410fd394'
    ],
    [
        'libavformat/oggdec.h', License.OGG_MA_MR_2005,
        'ee65196bafec5d8e871e64bb739bdc79'
    ],
    [
        'libavformat/oggparsevorbis.c', License.OGG_MA_MR_2005,
        '6c432580b4486564e43cd538370e3dbc'
    ],
]

# Path describing 'license_texts' folder as a sibling of this script's location.
LICENSE_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                              'license_texts')

# Files containing license text to be used for the known license buckets. These
# files should all live in LICENSE_FOLDER.
LICENSE_TEXTS = {
    License.MIPS:
    os.path.join(LICENSE_FOLDER, 'mips.txt'),
    License.JPEG:
    os.path.join(LICENSE_FOLDER, 'jpeg.txt'),
    License.LGPL:
    os.path.join(LICENSE_FOLDER, 'full_lgpl.txt'),
    License.OGG_MA_MR_2005:
    os.path.join(LICENSE_FOLDER, 'oggparse_ahlberg_rullgayrd_2005.txt'),
}


class CreditsUpdater(object):
    """CreditsUpdater parses license headers for files supplied via ProcessFile.
  The parsed headers are stored for generating the FFmpeg credits file
  (LICENSE.md) upon calling OutputCredits."""

    def __init__(self, source_dir, output_file=DEFAULT_OUTPUT_FILE):
        """ Creates a CreditsUpdater
    Args:
      source_dir: Root of ffmpeg sources; where LICENSE.md is found and where
        the generated DEFAULT_OUTPUT_FILE will be written.
      output_file: (Optional) Name of the file to write the credits to. File
        will live in source_dir.
    """
        self.source_dir = source_dir
        self.output_file = output_file
        # Files where we failed to find any license header. Any entry in this list
        # will block updating credits until the parsing code is amended to work for
        # the difficult files.
        self.difficult_files = []
        # Map storing processed files that belong to KNOWN_FILE_BUCKETS.
        # Key: LICENSE, Value: List of files with the known license.
        self.known_credits = collections.defaultdict(list)
        # Map storing processed files that do not belong to any known bucket. These
        # files will have their license printed verbatim.
        # Key: file path, Value: license text
        self.generated_credits = collections.defaultdict(list)
        # Convert the "buckets" above into a map.
        self.known_file_map = {}
        for item in KNOWN_FILE_BUCKETS:
            self.known_file_map[os.path.join(item[0])] = FileInfo(
                item[1], item[2])

    def ProcessFile(self, file_path):
        """ Process the file updating credits.
    Args:
      file_path: Path to file to process. Path can be absolute or relative, but
      should be a descendant of source_dir provided to constructor.
    """
        if not os.path.isabs(file_path):
            file_path = os.path.abspath(
                os.path.join(self.source_dir, file_path))

        comment_lines = ExtractFirstCommentBlock(file_path)
        if not comment_lines:
            self.difficult_files.append(file_path)
            return

        # Try to pull out customizations in first few lines of license header before
        # "This file is part of FFmpeg." Failing to normalize indicates either a
        # totally different header or a header with significant alterations.
        normalized_lines = NormalizeCommentLines(comment_lines)
        if normalized_lines:
            sim_ratio = (difflib.SequenceMatcher(None,
                                                 ConcatLines(normalized_lines),
                                                 FFMPEG_LGPL_REF).ratio())

            # File is a close match to typical LGPL case.
            if sim_ratio >= LGPL_MATCH_THRESHOLD:
                self.known_credits[License.LGPL].append(file_path)
            # File matches some LGPL, but has significant differences.
            else:
                self.HandleNonLGPLFile(comment_lines, file_path)
        # File does not contain FFmpeg LGPL header in any form.
        else:
            self.HandleNonLGPLFile(comment_lines, file_path)

    def HandleNonLGPLFile(self, comment_lines, file_path):
        # Make file_path relative to FFmpeg directory to lookup self.known_file_map.
        rel_file_path = os.path.relpath(file_path,
                                        os.path.abspath(self.source_dir))

        # Many non-LGPL files fall into known groups (e.g. MIPS). We bucket these
        # together to avoid repeating the same license text in the credits.
        if rel_file_path in self.known_file_map:
            hasher = hashlib.md5()
            hasher.update(ConcatLines(comment_lines).encode('utf-8'))

            # Detect changes to file's licensing header.
            file_license_info = self.known_file_map[rel_file_path]
            if hasher.hexdigest() != file_license_info.license_digest:
                exit(
                    'File %(file_path)s header has changed (was: %(old_digest)s '
                    'now: %(new_digest)s). Inspect the header and update the '
                    'exceptions table to continue generating credits.' % {
                        'file_path': rel_file_path,
                        'old_digest': file_license_info.license_digest,
                        'new_digest': hasher.hexdigest()
                    })
            # Store known files in a list for printing.
            self.known_credits[file_license_info.license].append(rel_file_path)
        else:
            # This file does have a known bucket. We'll print its license verbatim.
            self.generated_credits[rel_file_path] = ConcatLines(
                comment_lines).strip()

    def PrintStats(self):
        num_known_credits = 0
        for license_bucket in self.known_credits:
            num_known_credits += len(self.known_credits[license_bucket])
        print('CreditsUpdater stats:')
        print(f'\t{num_known_credits} files w/ known_credits')
        print(f'\t{len(self.generated_credits.keys())} generated_credits')
        print(f'\t{len(self.difficult_files)} difficult_files files')

    def WriteCredits(self):
        if self.difficult_files:
            # After taking a closer look, enhance this tool to work for these or
            # add them to the white-list if they truly have no licensing header.
            print('Failed to find license header for these files:')
            for filename in self.difficult_files:
                print(filename)
            exit(
                'Update script to work for these to continue generating credits'
            )

        output_path = os.path.join(self.source_dir, self.output_file)
        licence_md_path = os.path.join(self.source_dir, UPSTREAM_LICENSEMD)
        with open(output_path, 'w') as open_output:
            # Always write the FFmpeg overview (LICENSE.md) first.
            with open(licence_md_path) as open_license_md:
                open_output.writelines(open_license_md.readlines())

            # Next write verbatim headers from the generated credits map.
            for filename, file_license in sorted(
                    self.generated_credits.items(), key=lambda x: x[0]):
                open_output.writelines(LICENSE_SEPARATOR)
                open_output.writelines('%s\n\n%s' % (filename, file_license))

            # Write the known licenses, ending with LGPL.
            for known_license in sorted(self.known_credits.keys()):
                # Skip LGPL for now. We print it at the end.
                if known_license is License.LGPL:
                    continue

                file_list = sorted(self.known_credits[known_license])
                with open(LICENSE_TEXTS[known_license]) as license_text:
                    open_output.writelines(LICENSE_SEPARATOR)
                    open_output.writelines('\n'.join(file_list) + '\n\n')
                    open_output.writelines(license_text.readlines())

            # Finally, write full text of LGPL
            with open(LICENSE_TEXTS[License.LGPL]) as lgpl_text:
                open_output.writelines(LICENSE_SEPARATOR)
                open_output.writelines(lgpl_text.readlines())


def ConcatLines(lines):
    return ''.join(lines)


def NormalizeCommentLines(comment_lines):
    # Copy to leave orig const.
    comment_lines = list(comment_lines)

    # Find start of ffmpeg lgpl header.
    line_index = 0
    for line in comment_lines:
        if (FFMPEG_HEADER_START.search(line)):
            break
        line_index += 1

    if line_index == len(comment_lines):
        # print "Failed to find start of ffmpeg header"
        return None

    # Typically just a few lines for copyright and file description. More
    # than 20 to the start hints that this may not be the typical lgpl header.
    if line_index > 20:
        # print "Header start too far from the top of comment"
        return None

    # Pull out stuff before header start.
    comment_lines = comment_lines[line_index:len(comment_lines)]
    return comment_lines


def ExtractFirstCommentBlock(file_path):
    lines = []
    found_comment_start = False
    found_comment_end = False
    is_asm = file_path.endswith('.asm')

    with open(file_path) as open_file:
        # .S files generally have C style block comments, but a handful have a
        # special single-line comment prefixed with '@'. Check a few lines to figure
        # out which case we're dealing with.
        if file_path.endswith('.S'):
            first_line = open_file.readline()
            if ASM_COMMENT_PRE.search(first_line):
                is_asm = True
            open_file.seek(0)

        if is_asm:
            comment_start_re = ASM_COMMENT_PRE
            comment_end_re = ASM_NOT_COMMENT
        else:
            comment_start_re = C_COMMENT_BLOCK_START
            comment_end_re = C_COMMENT_BLOCK_END

        for _ in range(0, 100):
            line = open_file.readline()
            found_comment_start = (found_comment_start
                                   or comment_start_re.search(line))
            if not found_comment_start:
                continue

            lines.append(line)
            if comment_end_re.search(line):
                found_comment_end = True
                break

    if not (found_comment_start and found_comment_end):
        return None

    StripCommentChars(lines, is_asm)
    return lines


def StripCommentChars(comment_lines, is_asm=False):
    if is_asm:
        for i in range(len(comment_lines)):
            comment_lines[i] = re.sub(ASM_COMMENT_PRE, '', comment_lines[i])
    else:
        # Strip off the start slash-star
        comment_lines[0] = re.sub(C_COMMENT_BLOCK_START, '', comment_lines[0])
        # Strip off the comment end star-slash
        comment_lines[-1] = re.sub(C_COMMENT_BLOCK_END, '', comment_lines[-1])
        # Strip off the comment star for middle lines
        for i in range(1, len(comment_lines)):
            comment_lines[i] = re.sub(C_COMMENT_BLOCK_MID, '',
                                      comment_lines[i])
