Edit Project Badge Status
Projects that follow the best practices below can voluntarily self-certify and show that they've achieved an Open Source Security Foundation (OpenSSF) best practices badge. 

There is no set of practices that can guarantee that software will never have defects or vulnerabilities; even formal methods can fail if the specifications or assumptions are wrong. Nor is there any set of practices that can guarantee that a project will sustain a healthy and well-functioning development community. However, following best practices can help improve the results of projects. For example, some practices enable multi-person review before release, which can both help find otherwise hard-to-find technical vulnerabilities and help build trust and a desire for repeated interaction among developers from different companies. To earn a badge, all MUST and MUST NOT criteria must be met, all SHOULD criteria must be met OR be unmet with justification, and all SUGGESTED criteria must be met OR unmet (we want them considered at least). If you want to enter justification text as a generic comment, instead of being a rationale that the situation is acceptable, start the text block with '//' followed by a space. Feedback is welcome via the GitHub site as issues or pull requests There is also a mailing list for general discussion.

We gladly provide the information in several locales, however, if there is any conflict or inconsistency between the translations, the English version is the authoritative version.
Please 'submit' often to save your work (you can always go back and edit more later).

If you need help, have a question, or see a problem, please file an issue.

These are the Passing level criteria. You can also view the Silver or Gold level criteria.

Baseline Series:   

           

 Basics7/13 ●
General
🤖 What is the human-readable name of the project? 
Note that other projects may use the same name.
job-sentinel
🤖 What is a brief description of the project? 
Include key comments about the project. Use markdown. This information is used when displaying badge information.
Site-agnostic job-portal monitor with pluggable adapters and instant Telegram alerts.
What language is used for this badge entry's description and justifications? 
Select the language used for the project description and criterion justification text. This helps browser translation tools correctly identify the language of this content. Most projects use English.

English (en)
What is the URL for the project (as a whole)?
https://job-sentinel.vercel.app
What is the URL for the version control repository (it may be the same as the project URL)?
https://github.com/harshitwandhare/job-sentinel
🤖 What license(s) is the project released under? 
Please use SPDX license expression format; examples include "Apache-2.0", "BSD-2-Clause", "BSD-3-Clause", "GPL-2.0+", "LGPL-3.0+", "MIT", and "(BSD-2-Clause OR Ruby)". Do not include single quotes or double quotes.
MIT
🤖 What programming language(s) are used to implement the project? 
If there is more than one language, list them as comma-separated values (spaces optional) and sort them from most to least used. If there is a long list, please list at least the first three most common ones. If there is no language (e.g., this is a documentation-only or test-only project), use the single character "-". Please use a conventional capitalization for each language, e.g., "JavaScript".
Python, TypeScript, Jinja, Dockerfile, JavaScript
What is the Common Platform Enumeration (CPE) name for the project (if it has one)? 
The Common Platform Enumeration (CPE) is a structured naming scheme for information technology systems, software, and packages. It is used in a number of systems and databases when reporting vulnerabilities.
(Optional) CPE name
Other general comments about the project:
Additional Comments (in markdown)
Basic project website content

Unknown required information, not enough for a badge.
Met
Unmet
?

The project website MUST succinctly describe what the software does (what problem does it solve?). [description_good] 
This MUST be in language that potential users can understand (e.g., it uses minimal jargon).
Description good justification

Unknown required information, not enough for a badge.
Met
Unmet
?

The project website MUST provide information on how to: obtain, provide feedback (as bug reports or enhancements), and contribute to the software. [interact]
Interact justification
🤖

Enough for a badge!
Met
Unmet
?

The information on how to contribute MUST explain the contribution process (e.g., are pull requests used?) (URL required) [contribution] 
We presume that projects on GitHub use issues and pull requests unless otherwise noted. This information can be short, e.g., stating that the project uses pull requests, an issue tracker, or posts to a mailing list (which one?)
Contribution justification
Non-trivial contribution file in repository: <https://github.com/harshitwandhare/job-sentinel/blob/main/CONTRIBUTING.md>.

Unknown required information, not enough for a badge.
Met
Unmet
?

The information on how to contribute SHOULD include the requirements for acceptable contributions (e.g., a reference to any required coding standard). (URL required) [contribution_requirements]
Contribution requirements justification

FLOSS license
🤖

Enough for a badge!
Met
Unmet
?

The software produced by the project MUST be released as FLOSS. [floss_license] 
FLOSS is software released in a way that meets the Open Source Definition or Free Software Definition. Examples of such licenses include the CC0, MIT, BSD 2-clause, BSD 3-clause revised, Apache 2.0, Lesser GNU General Public License (LGPL), and the GNU General Public License (GPL). For our purposes, this means that the license MUST be:
an approved license by the Open Source Initiative (OSI), or
a free license as approved by the Free Software Foundation (FSF), or
a free license acceptable to Debian main, or
a "good" license according to Fedora.
The software MAY also be licensed other ways (e.g., "GPLv2 or proprietary" is acceptable).
Floss license justification
The MIT license is approved by the Open Source Initiative (OSI).
🤖

Enough for a badge!
Met
Unmet
?

It is SUGGESTED that any required license(s) for the software produced by the project be approved by the Open Source Initiative (OSI). [floss_license_osi] 
The OSI uses a rigorous approval process to determine which licenses are OSS.
Floss license osi justification
The MIT license is approved by the Open Source Initiative (OSI).
🤖

Enough for a badge!
Met
Unmet
?

The project MUST post the license(s) of its results in a standard location in their source repository. (URL required) [license_location] 
One convention is posting the license as a top-level file named LICENSE or COPYING, which MAY be followed by an extension such as ".txt" or ".md". An alternative convention is to have a directory named LICENSES containing license file(s); these files are typically named as their SPDX license identifier followed by an appropriate file extension, as described in the REUSE Specification. Note that this criterion is only a requirement on the source repository. You do NOT need to include the license file when generating something from the source code (such as an executable, package, or container). For example, when generating an R package for the Comprehensive R Archive Network (CRAN), follow standard CRAN practice: if the license is a standard license, use the standard short license specification (to avoid installing yet another copy of the text) and list the LICENSE file in an exclusion file such as .Rbuildignore. Similarly, when creating a Debian package, you may put a link in the copyright file to the license text in /usr/share/common-licenses, and exclude the license file from the created package (e.g., by deleting the file after calling dh_auto_install). We encourage including machine-readable license information in generated formats where practical.
License location justification
Non-trivial license location file in repository: <https://github.com/harshitwandhare/job-sentinel/blob/main/LICENSE>.

Documentation
🤖

Enough for a badge!
Met
Unmet
N/A
?

The project MUST provide basic documentation for the software produced by the project. [documentation_basics] 
This documentation must be in some media (such as text or video) that includes: how to install it, how to start it, how to use it (possibly with a tutorial using examples), and how to use it securely (e.g., what to do and what not to do) if that is an appropriate topic for the software. The security documentation need not be long. The project MAY use hypertext links to non-project material as documentation. If the project does not produce software, choose "not applicable" (N/A).
Documentation basics justification
Some documentation basics file contents found.

Unknown required information, not enough for a badge.
Met
Unmet
N/A
?

The project MUST provide reference documentation that describes the external interface (both input and output) of the software produced by the project. [documentation_interface] 
The documentation of an external interface explains to an end-user or developer how to use it. This would include its application program interface (API) if the software has one. If it is a library, document the major classes/types and methods/functions that can be called. If it is a web application, define its URL interface (often its REST interface). If it is a command-line interface, document the parameters and options it supports. In many cases it's best if most of this documentation is automatically generated, so that this documentation stays synchronized with the software as it changes, but this isn't required. The project MAY use hypertext links to non-project material as documentation. Documentation MAY be automatically generated (where practical this is often the best way to do so). Documentation of a REST interface may be generated using Swagger/OpenAPI. Code interface documentation MAY be generated using tools such as JSDoc (JavaScript), ESDoc (JavaScript), pydoc (Python), devtools (R), pkgdown (R), and Doxygen (many). Merely having comments in implementation code is not sufficient to satisfy this criterion; there needs to be an easy way to see the information without reading through all the source code. If the project does not produce software, choose "not applicable" (N/A).
Documentation interface justification

Other
🤖

Enough for a badge!
Met
Unmet
?

The project sites (website, repository, and download URLs) MUST support HTTPS using TLS. [sites_https] 
This requires that the project home page URL and the version control repository URL begin with "https:", not "http:". You can get free certificates from Let's Encrypt. Projects MAY implement this criterion using (for example) GitHub pages, GitLab pages, or SourceForge project pages. If you support HTTP, we urge you to redirect the HTTP traffic to HTTPS.
Sites https justification
Given only https: URLs.
🤖

Enough for a badge!
Met
Unmet
?

The project MUST have one or more mechanisms for discussion (including proposed changes and issues) that are searchable, allow messages and topics to be addressed by URL, enable new people to participate in some of the discussions, and do not require client-side installation of proprietary software. [discussion] 
Examples of acceptable mechanisms include archived mailing list(s), GitHub issue and pull request discussions, Bugzilla, Mantis, and Trac. Asynchronous discussion mechanisms (like IRC) are acceptable if they meet these criteria; make sure there is a URL-addressable archiving mechanism. Proprietary JavaScript, while discouraged, is permitted.
Discussion justification
GitHub supports discussions on issues and pull requests.

Unknown required information, not enough for a badge.
Met
Unmet
?

The project SHOULD provide documentation in English and be able to accept bug reports and comments about code in English. [english] 
English is currently the lingua franca of computer technology; supporting English increases the number of different potential developers and reviewers worldwide. A project can meet this criterion even if its core developers' primary language is not English.
English justification

Unknown required information, not enough for a badge.
Met
Unmet
?

The project MUST be maintained. [maintained] 
As a minimum, the project should attempt to respond to significant problem and vulnerability reports. A project that is actively pursuing a badge is probably maintained. All projects and people have limited resources, and typical projects must reject some proposed changes, so limited resources and proposal rejections do not by themselves indicate an unmaintained project.

When a project knows that it will no longer be maintained, it should set this criterion to "Unmet" and use the appropriate mechanism(s) to indicate to others that it is not being maintained. For example, use “DEPRECATED” as the first heading of its README, add “DEPRECATED” near the beginning of its home page, add “DEPRECATED” to the beginning of its code repository project description, add a no-maintenance-intended badge in its README and/or home page, mark it as deprecated in any package repositories (e.g., npm deprecate), and/or use the code repository's marking system to archive it (e.g., GitHub's "archive" setting, GitLab’s "archived" marking, Gerrit's "readonly" status, or SourceForge’s "abandoned" project status). Additional discussion can be found here.
Maintained justification

By submitting this data about the project you agree to release it under at least the Community Data License Agreement – Permissive, Version 2.0. This means that a Data Recipient may share the Data, with or without modifications, so long as the Data Recipient makes available the text of this agreement with the shared Data. This agreement does not impose any restriction or obligations with respect to the use, modification, or sharing of Results. You retain copyright (if any), and the project license is unaffected.

You can use tools and AI systems to propose changes via a simple URL, such as https://www.bestpractices.dev/en/projects/13183/choose/edit?osps_ac_01_01_status=Met&osps_ac_01_01_justification=GitHub+enforced. See our automation proposals system for how to do that.

 
 Change Control4/9 ●
Public version-controlled source repository
🤖

Enough for a badge!
Met
Unmet
?

The project MUST have a version-controlled source repository that is publicly readable and has a URL. [repo_public] 
The URL MAY be the same as the project URL. The project MAY use private (non-public) branches in specific cases while the change is not publicly released (e.g., for fixing a vulnerability before it is revealed to the public).
Repo public justification
Repository on GitHub, which provides public git repositories with URLs.
🤖

Enough for a badge!
Met
Unmet
?

The project's source repository MUST track what changes were made, who made the changes, and when the changes were made. [repo_track]
Repo track justification
Repository on GitHub, which uses git. git can track the changes, who made them, and when they were made.

Unknown required information, not enough for a badge.
Met
Unmet
?

To enable collaborative review, the project's source repository MUST include interim versions for review between releases; it MUST NOT include only final releases. [repo_interim] 
Projects MAY choose to omit specific interim versions from their public source repositories (e.g., ones that fix specific non-public security vulnerabilities, may never be publicly released, or include material that cannot be legally posted and are not in the final release).
Repo interim justification
🤖

Enough for a badge!
Met
Unmet
?

It is SUGGESTED that common distributed version control software be used (e.g., git) for the project's source repository. [repo_distributed] 
Git is not specifically required and projects can use centralized version control software (such as subversion) with justification.
Repo distributed justification
Repository on GitHub, which uses git. git is distributed.

Unique version numbering

Unknown required information, not enough for a badge.
Met
Unmet
?

The project results MUST have a unique version identifier for each release intended to be used by users. [version_unique] 
This MAY be met in a variety of ways including a commit IDs (such as git commit id or mercurial changeset id) or a version number (including version numbers that use semantic versioning or date-based schemes like YYYYMMDD).
Version unique justification

Unknown required information, not enough for a badge.
Met
Unmet
?

It is SUGGESTED that the Semantic Versioning (SemVer) or Calendar Versioning (CalVer) version numbering format be used for releases. It is SUGGESTED that those who use CalVer include a micro level value. [version_semver] 
Projects should generally prefer whatever format is expected by their users, e.g., because it is the normal format used by their ecosystem. Many ecosystems prefer SemVer, and SemVer is generally preferred for application programmer interfaces (APIs) and software development kits (SDKs). CalVer tends to be used by projects that are large, have an unusually large number of independently-developed dependencies, have a constantly-changing scope, or are time-sensitive. It is SUGGESTED that those who use CalVer include a micro level value, because including a micro level supports simultaneously-maintained branches whenever that becomes necessary. Other version numbering formats may be used as version numbers, including git commit IDs or mercurial changeset IDs, as long as they uniquely identify versions. However, some alternatives (such as git commit IDs) can cause problems as release identifiers, because users may not be able to easily determine if they are up-to-date. The version ID format may be unimportant for identifying software releases if all recipients only run the latest version (e.g., it is the code for a single website or internet service that is constantly updated via continuous delivery).
Version semver justification

Unknown required information, not enough for a badge.
Met
Unmet
?

It is SUGGESTED that projects identify each release within their version control system. For example, it is SUGGESTED that those using git identify each release using git tags. [version_tags]
Version tags justification

Release notes
🤖

Enough for a badge!
Met
Unmet
N/A
?

The project MUST provide, in each release, release notes that are a human-readable summary of major changes in that release to help users determine if they should upgrade and what the upgrade impact will be. The release notes MUST NOT be the raw output of a version control log (e.g., the "git log" command results are not release notes). Projects whose results are not intended for reuse in multiple locations (such as the software for a single website or service) AND employ continuous delivery MAY select "N/A". (URL required) [release_notes] 
The release notes MAY be implemented in a variety of ways. Many projects provide them in a file named "NEWS", "CHANGELOG", or "ChangeLog", optionally with extensions such as ".txt", ".md", or ".html". Historically the term "change log" meant a log of every change, but to meet these criteria what is needed is a human-readable summary. The release notes MAY instead be provided by version control system mechanisms such as the GitHub Releases workflow.
Release notes justification
Non-trivial release notes file in repository: <https://github.com/harshitwandhare/job-sentinel/blob/main/CHANGELOG.md>.

Unknown required information, not enough for a badge.
Met
Unmet
N/A
?

The release notes MUST identify every publicly known run-time vulnerability fixed in this release that already had a CVE assignment or similar when the release was created. This criterion may be marked as not applicable (N/A) if users typically cannot practically update the software themselves (e.g., as is often true for kernel updates). This criterion applies only to the project results, not to its dependencies. If there are no release notes or there have been no publicly known vulnerabilities, choose N/A. [release_notes_vulns] 
This criterion helps users determine if a given update will fix a vulnerability that is publicly known, to help users make an informed decision about updating. If users typically cannot practically update the software themselves on their computers, but must instead depend on one or more intermediaries to perform the update (as is often the case for a kernel and low-level software that is intertwined with a kernel), the project may choose "not applicable" (N/A) instead, since this additional information will not be helpful to those users. Similarly, a project may choose N/A if all recipients only run the latest version (e.g., it is the code for a single website or internet service that is constantly updated via continuous delivery). This criterion only applies to the project results, not its dependencies. Listing the vulnerabilities of all transitive dependencies of a project becomes unwieldy as dependencies increase and vary, and is unnecessary since tools that examine and track dependencies can do this in a more scalable way.
Release notes vulns justification

By submitting this data about the project you agree to release it under at least the Community Data License Agreement – Permissive, Version 2.0. This means that a Data Recipient may share the Data, with or without modifications, so long as the Data Recipient makes available the text of this agreement with the shared Data. This agreement does not impose any restriction or obligations with respect to the use, modification, or sharing of Results. You retain copyright (if any), and the project license is unaffected.

You can use tools and AI systems to propose changes via a simple URL, such as https://www.bestpractices.dev/en/projects/13183/choose/edit?osps_ac_01_01_status=Met&osps_ac_01_01_justification=GitHub+enforced. See our automation proposals system for how to do that.

 
 Reporting1/8 ●
Bug-reporting process
🤖

Enough for a badge!
Met
Unmet
?

The project MUST provide a process for users to submit bug reports (e.g., using an issue tracker or a mailing list). (URL required) [report_process]
Report process justification
Non-trivial SECURITY[.md] file found file in repository: <https://github.com/harshitwandhare/job-sentinel/blob/main/SECURITY.md>. [osps_do_02_01]

Unknown required information, not enough for a badge.
Met
Unmet
?

The project SHOULD use an issue tracker for tracking individual issues. [report_tracker]
Report tracker justification

Unknown required information, not enough for a badge.
Met
Unmet
?

The project MUST acknowledge a majority of bug reports submitted in the last 2-12 months (inclusive); the response need not include a fix. [report_responses]
Report responses justification

Unknown required information, not enough for a badge.
Met
Unmet
?

The project SHOULD respond to a majority (>50%) of enhancement requests in the last 2-12 months (inclusive). [enhancement_responses] 
The response MAY be 'no' or a discussion about its merits. The goal is simply that there be some response to some requests, which indicates that the project is still alive. For purposes of this criterion, projects need not count fake requests (e.g., from spammers or automated systems). If a project is no longer making enhancements, please select "unmet" and include the URL that makes this situation clear to users. If a project tends to be overwhelmed by the number of enhancement requests, please select "unmet" and explain.
Enhancement responses justification

Unknown required information, not enough for a badge.
Met
Unmet
?

The project MUST have a publicly available archive for reports and responses for later searching. (URL required) [report_archive]
Report archive justification

Vulnerability report process

Unknown required information, not enough for a badge.
Met
Unmet
?

The project MUST publish the process for reporting vulnerabilities on the project site. (URL required) [vulnerability_report_process] 
Projects hosted on GitHub SHOULD consider enabling privately reporting a security vulnerability. Projects on GitLab SHOULD consider using its ability for privately reporting a vulnerability. Projects MAY identify a mailing address on https://PROJECTSITE/security, often in the form security@example.org. This vulnerability reporting process MAY be the same as its bug reporting process. Vulnerability reports MAY always be public, but many projects have a private vulnerability reporting mechanism.
Vulnerability report process justification

Unknown required information, not enough for a badge.
Met
Unmet
N/A
?

If private vulnerability reports are supported, the project MUST include how to send the information in a way that is kept private. (URL required) [vulnerability_report_private] 
Examples include a private defect report submitted on the web using HTTPS (TLS) or an email encrypted using OpenPGP. If vulnerability reports are always public (so there are never private vulnerability reports), choose "not applicable" (N/A).
Vulnerability report private justification

Unknown required information, not enough for a badge.
Met
Unmet
N/A
?

The project's initial response time for any vulnerability report received in the last 6 months MUST be less than or equal to 14 days. [vulnerability_report_response] 
If there have been no vulnerabilities reported in the last 6 months, choose "not applicable" (N/A).
Vulnerability report response justification

By submitting this data about the project you agree to release it under at least the Community Data License Agreement – Permissive, Version 2.0. This means that a Data Recipient may share the Data, with or without modifications, so long as the Data Recipient makes available the text of this agreement with the shared Data. This agreement does not impose any restriction or obligations with respect to the use, modification, or sharing of Results. You retain copyright (if any), and the project license is unaffected.

You can use tools and AI systems to propose changes via a simple URL, such as https://www.bestpractices.dev/en/projects/13183/choose/edit?osps_ac_01_01_status=Met&osps_ac_01_01_justification=GitHub+enforced. See our automation proposals system for how to do that.

 
 Quality0/13 ●
Working build system

Unknown required information, not enough for a badge.
Met
Unmet
N/A
?

If the software produced by the project requires building for use, the project MUST provide a working build system that can automatically rebuild the software from source code. [build] 
A build system determines what actions need to occur to rebuild the software (and in what order), and then performs those steps. For example, it can invoke a compiler to compile the source code. If an executable is created from source code, it must be possible to modify the project's source code and then generate an updated executable with those modifications. If the software produced by the project depends on external libraries, the build system does not need to build those external libraries. If there is no need to build anything to use the software after its source code is modified, select "not applicable" (N/A).
Build justification

Unknown required information, not enough for a badge.
Met
Unmet
N/A
?

It is SUGGESTED that common tools be used for building the software. [build_common_tools] 
For example, Maven, Ant, cmake, the autotools, make, rake (Ruby), or devtools (R).
Build common tools justification

Unknown required information, not enough for a badge.
Met
Unmet
N/A
?

The project SHOULD be buildable using only FLOSS tools. [build_floss_tools]
Build floss tools justification

Automated test suite

Unknown required information, not enough for a badge.
Met
Unmet
?

The project MUST use at least one automated test suite that is publicly released as FLOSS (this test suite may be maintained as a separate FLOSS project). The project MUST clearly show or document how to run the test suite(s) (e.g., via a continuous integration (CI) script or via documentation in files such as BUILD.md, README.md, or CONTRIBUTING.md). [test] 
The project MAY use multiple automated test suites (e.g., one that runs quickly, vs. another that is more thorough but requires special equipment). There are many test frameworks and test support systems available, including Selenium (web browser automation), Junit (JVM, Java), RUnit (R), testthat (R).
Test justification

Unknown required information, not enough for a badge.
Met
Unmet
?

A test suite SHOULD be invocable in a standard way for that language. [test_invocation] 
For example, "make check", "mvn test", or "rake test" (Ruby).
Test invocation justification

Unknown required information, not enough for a badge.
Met
Unmet
?

It is SUGGESTED that the test suite cover most (or ideally all) the code branches, input fields, and functionality. [test_most]
Test most justification

Unknown required information, not enough for a badge.
Met
Unmet
?

It is SUGGESTED that the project implement continuous integration (where new or changed code is frequently integrated into a central code repository and automated tests are run on the result). [test_continuous_integration]
Test continuous integration justification

New functionality testing

Unknown required information, not enough for a badge.
Met
Unmet
?

The project MUST have a general policy (formal or not) that as major new functionality is added to the software produced by the project, tests of that functionality should be added to an automated test suite. [test_policy] 
As long as a policy is in place, even by word of mouth, that says developers should add tests to the automated test suite for major new functionality, select "Met."
Test policy justification

Unknown required information, not enough for a badge.
Met
Unmet
?

The project MUST have evidence that the test_policy for adding tests has been adhered to in the most recent major changes to the software produced by the project. [tests_are_added] 
Major functionality would typically be mentioned in the release notes. Perfection is not required, merely evidence that tests are typically being added in practice to the automated test suite when new major functionality is added to the software produced by the project.
Tests are added justification

Unknown required information, not enough for a badge.
Met
Unmet
?

It is SUGGESTED that this policy on adding tests (see test_policy) be documented in the instructions for change proposals. [tests_documented_added] 
However, even an informal rule is acceptable as long as the tests are being added in practice.
Tests documented added justification

Warning flags

Unknown required information, not enough for a badge.
Met
Unmet
N/A
?

The project MUST enable one or more compiler warning flags, a "safe" language mode, or use a separate "linter" tool to look for code quality errors or common simple mistakes, if there is at least one FLOSS tool that can implement this criterion in the selected language. [warnings] 
Examples of compiler warning flags include gcc/clang "-Wall". Examples of a "safe" language mode include JavaScript "use strict" and perl5's "use warnings". A separate "linter" tool is simply a tool that examines the source code to look for code quality errors or common simple mistakes. These are typically enabled within the source code or build instructions.
Warnings justification

Unknown required information, not enough for a badge.
Met
Unmet
N/A
?

The project MUST address warnings. [warnings_fixed] 
These are the warnings identified by the implementation of the warnings criterion. The project should fix warnings or mark them in the source code as false positives. Ideally there would be no warnings, but a project MAY accept some warnings (typically less than 1 warning per 100 lines or less than 10 warnings).
Warnings fixed justification

Unknown required information, not enough for a badge.
Met
Unmet
N/A
?

It is SUGGESTED that projects be maximally strict with warnings in the software produced by the project, where practical. [warnings_strict] 
Some warnings cannot be effectively enabled on some projects. What is needed is evidence that the project is striving to enable warning flags where it can, so that errors are detected early.
Warnings strict justification

By submitting this data about the project you agree to release it under at least the Community Data License Agreement – Permissive, Version 2.0. This means that a Data Recipient may share the Data, with or without modifications, so long as the Data Recipient makes available the text of this agreement with the shared Data. This agreement does not impose any restriction or obligations with respect to the use, modification, or sharing of Results. You retain copyright (if any), and the project license is unaffected.

You can use tools and AI systems to propose changes via a simple URL, such as https://www.bestpractices.dev/en/projects/13183/choose/edit?osps_ac_01_01_status=Met&osps_ac_01_01_justification=GitHub+enforced. See our automation proposals system for how to do that.

 
 Security1/16 ●
Secure development knowledge

Unknown required information, not enough for a badge.
Met
Unmet
?

The project MUST have at least one primary developer who knows how to design secure software. (See ‘details’ for the exact requirements.) [know_secure_design] 
This requires understanding the following design principles, including the 8 principles from Saltzer and Schroeder:
economy of mechanism (keep the design as simple and small as practical, e.g., by adopting sweeping simplifications)
fail-safe defaults (access decisions should deny by default, and projects' installation should be secure by default)
complete mediation (every access that might be limited must be checked for authority and be non-bypassable)
open design (security mechanisms should not depend on attacker ignorance of its design, but instead on more easily protected and changed information like keys and passwords)
separation of privilege (ideally, access to important objects should depend on more than one condition, so that defeating one protection system won't enable complete access. E.G., multi-factor authentication, such as requiring both a password and a hardware token, is stronger than single-factor authentication)
least privilege (processes should operate with the least privilege necessary)
least common mechanism (the design should minimize the mechanisms common to more than one user and depended on by all users, e.g., directories for temporary files)
psychological acceptability (the human interface must be designed for ease of use - designing for "least astonishment" can help)
limited attack surface (the attack surface - the set of the different points where an attacker can try to enter or extract data - should be limited)
input validation with allowlists (inputs should typically be checked to determine if they are valid before they are accepted; this validation should use allowlists (which only accept known-good values), not denylists (which attempt to list known-bad values)).
A "primary developer" in a project is anyone who is familiar with the project's code base, is comfortable making changes to it, and is acknowledged as such by most other participants in the project. A primary developer would typically make a number of contributions over the past year (via code, documentation, or answering questions). Developers would typically be considered primary developers if they initiated the project (and have not left the project more than three years ago), have the option of receiving information on a private vulnerability reporting channel (if there is one), can accept commits on behalf of the project, or perform final releases of the project software. If there is only one developer, that individual is the primary developer. Many books and courses are available to help you understand how to develop more secure software and discuss design. For example, the Secure Software Development Fundamentals course is a free set of three courses that explain how to develop more secure software (it's free if you audit it; for an extra fee you can earn a certificate to prove you learned the material).
Know secure design justification

Unknown required information, not enough for a badge.
Met
Unmet
?

At least one of the project's primary developers MUST know of common kinds of errors that lead to vulnerabilities in this kind of software, as well as at least one method to counter or mitigate each of them. [know_common_errors] 
Examples (depending on the type of software) include SQL injection, OS injection, classic buffer overflow, cross-site scripting, missing authentication, and missing authorization. See the CWE/SANS top 25 or OWASP Top 10 for commonly used lists. Many books and courses are available to help you understand how to develop more secure software and discuss common implementation errors that lead to vulnerabilities. For example, the Secure Software Development Fundamentals course is a free set of three courses that explain how to develop more secure software (it's free if you audit it; for an extra fee you can earn a certificate to prove you learned the material).
Know common errors justification

Use basic good cryptographic practices
Note that some software does not need to use cryptographic mechanisms. If your project produces software that (1) includes, activates, or enables encryption functionality, and (2) might be released from the United States (US) to outside the US or to a non-US-citizen, you may be legally required to take a few extra steps. Typically this just involves sending an email. For more information, see the encryption section of Understanding Open Source Technology & US Export Controls.



Unknown required information, not enough for a badge.
Met
Unmet
N/A
?

The software produced by the project MUST use, by default, only cryptographic protocols and algorithms that are publicly published and reviewed by experts (if cryptographic protocols and algorithms are used). [crypto_published] 
These cryptographic criteria do not always apply because some software has no need to directly use cryptographic capabilities.
Crypto published justification

Unknown required information, not enough for a badge.
Met
Unmet
N/A
?

If the software produced by the project is an application or library, and its primary purpose is not to implement cryptography, then it SHOULD only call on software specifically designed to implement cryptographic functions; it SHOULD NOT re-implement its own. [crypto_call]
Crypto call justification

Unknown required information, not enough for a badge.
Met
Unmet
N/A
?

All functionality in the software produced by the project that depends on cryptography MUST be implementable using FLOSS. [crypto_floss] 
See the Open Standards Requirement for Software by the Open Source Initiative.
Crypto floss justification

Unknown required information, not enough for a badge.
Met
Unmet
N/A
?

The security mechanisms within the software produced by the project MUST use default keylengths that at least meet the NIST minimum requirements through the year 2030 (as stated in 2012). It MUST be possible to configure the software so that smaller keylengths are completely disabled. [crypto_keylength] 
These minimum bitlengths are: symmetric key 112, factoring modulus 2048, discrete logarithm key 224, discrete logarithmic group 2048, elliptic curve 224, and hash 224 (password hashing is not covered by this bitlength, more information on password hashing can be found in the crypto_password_storage criterion). See https://www.keylength.com for a comparison of keylength recommendations from various organizations. The software MAY allow smaller keylengths in some configurations (ideally it would not, since this allows downgrade attacks, but shorter keylengths are sometimes necessary for interoperability).
Crypto keylength justification

Unknown required information, not enough for a badge.
Met
Unmet
N/A
?

The default security mechanisms within the software produced by the project MUST NOT depend on broken cryptographic algorithms (e.g., MD4, MD5, single DES, RC4, Dual_EC_DRBG), or use cipher modes that are inappropriate to the context, unless they are necessary to implement an interoperable protocol (where the protocol implemented is the most recent version of that standard broadly supported by the network ecosystem, that ecosystem requires the use of such an algorithm or mode, and that ecosystem does not offer any more secure alternative). The documentation MUST describe any relevant security risks and any known mitigations if these broken algorithms or modes are necessary for an interoperable protocol. [crypto_working] 
ECB mode is almost never appropriate because it reveals identical blocks within the ciphertext as demonstrated by the ECB penguin, and CTR mode is often inappropriate because it does not perform authentication and causes duplicates if the input state is repeated. In many cases it's best to choose a block cipher algorithm mode designed to combine secrecy and authentication, e.g., Galois/Counter Mode (GCM) and EAX. Projects MAY allow users to enable broken mechanisms (e.g., during configuration) where necessary for compatibility, but then users know they're doing it.
Crypto working justification

Unknown required information, not enough for a badge.
Met
Unmet
N/A
?

The default security mechanisms within the software produced by the project SHOULD NOT depend on cryptographic algorithms or modes with known serious weaknesses (e.g., the SHA-1 cryptographic hash algorithm or the CBC mode in SSH). [crypto_weaknesses] 
Concerns about CBC mode in SSH are discussed in CERT: SSH CBC vulnerability.
Crypto weaknesses justification

Unknown required information, not enough for a badge.
Met
Unmet
N/A
?

The security mechanisms within the software produced by the project SHOULD implement perfect forward secrecy for key agreement protocols so a session key derived from a set of long-term keys cannot be compromised if one of the long-term keys is compromised in the future. [crypto_pfs]
Crypto pfs justification

Unknown required information, not enough for a badge.
Met
Unmet
N/A
?

If the software produced by the project causes the storing of passwords for authentication of external users, the passwords MUST be stored as iterated hashes with a per-user salt by using a key stretching (iterated) algorithm (e.g., Argon2id, Bcrypt, Scrypt, or PBKDF2). See also OWASP Password Storage Cheat Sheet. [crypto_password_storage] 
This criterion applies only when the software is enforcing authentication of users using passwords for external users (aka inbound authentication), such as server-side web applications. It does not apply in cases where the software stores passwords for authenticating into other systems (aka outbound authentication, e.g., the software implements a client for some other system), since at least parts of that software must have often access to the unhashed password.
Crypto password storage justification

Unknown required information, not enough for a badge.
Met
Unmet
N/A
?

The security mechanisms within the software produced by the project MUST generate all cryptographic keys and nonces using a cryptographically secure random number generator, and MUST NOT do so using generators that are cryptographically insecure. [crypto_random] 
A cryptographically secure random number generator may be a hardware random number generator, or it may be a cryptographically secure pseudo-random number generator (CSPRNG) using an algorithm such as Hash_DRBG, HMAC_DRBG, CTR_DRBG, Yarrow, or Fortuna. Examples of calls to secure random number generators include Java's java.security.SecureRandom and JavaScript's window.crypto.getRandomValues. Examples of calls to insecure random number generators include Java's java.util.Random and JavaScript's Math.random.
Crypto random justification

Secured delivery against man-in-the-middle (MITM) attacks
🤖

Enough for a badge!
Met
Unmet
?

The project MUST use a delivery mechanism that counters MITM attacks. Using https or ssh+scp is acceptable. [delivery_mitm] 
An even stronger mechanism is releasing the software with digitally signed packages, since that mitigates attacks on the distribution system, but this only works if the users can be confident that the public keys for signatures are correct and if the users will actually check the signature.
Delivery mitm justification
Distribution channels use HTTPS exclusively. [osps_br_03_02]

Unknown required information, not enough for a badge.
Met
Unmet
?

A cryptographic hash (e.g., a sha1sum) MUST NOT be retrieved over http and used without checking for a cryptographic signature. [delivery_unsigned] 
These hashes can be modified in transit.
Delivery unsigned justification

Publicly known vulnerabilities fixed

Unknown required information, not enough for a badge.
Met
Unmet
?

There MUST be no unpatched vulnerabilities of medium or higher severity that have been publicly known for more than 60 days. [vulnerabilities_fixed_60_days] 
The vulnerability must be patched and released by the project itself (patches may be developed elsewhere). A vulnerability becomes publicly known (for this purpose) once it has a CVE with publicly released non-paywalled information (reported, for example, in the National Vulnerability Database) or when the project has been informed and the information has been released to the public (possibly by the project). A vulnerability is considered medium or higher severity if its Common Vulnerability Scoring System (CVSS) base qualitative score is medium or higher. In CVSS versions 2.0 through 3.1, this is equivalent to a CVSS score of 4.0 or higher. Projects may use the CVSS score as published in a widely-used vulnerability database (such as the National Vulnerability Database) using the most-recent version of CVSS reported in that database. Projects may instead calculate the severity themselves using the latest version of CVSS at the time of the vulnerability disclosure, if the calculation inputs are publicly revealed once the vulnerability is publicly known. Note: this means that users might be left vulnerable to all attackers worldwide for up to 60 days. This criterion is often much easier to meet than what Google recommends in Rebooting responsible disclosure, because Google recommends that the 60-day period start when the project is notified even if the report is not public. Also note that this badge criterion, like other criteria, applies to the individual project. Some projects are part of larger umbrella organizations or larger projects, possibly in multiple layers, and many projects feed their results to other organizations and projects as part of a potentially-complex supply chain. An individual project often cannot control the rest, but an individual project can work to release a vulnerability patch in a timely way. Therefore, we focus solely on the individual project's response time. Once a patch is available from the individual project, others can determine how to deal with the patch (e.g., they can update to the newer version or they can apply just the patch as a cherry-picked solution).
Vulnerabilities fixed 60 days justification

Unknown required information, not enough for a badge.
Met
Unmet
?

Projects SHOULD fix all critical vulnerabilities rapidly after they are reported. [vulnerabilities_critical_fixed]
Vulnerabilities critical fixed justification

Other security issues

Unknown required information, not enough for a badge.
Met
Unmet
?

The public repositories MUST NOT leak a valid private credential (e.g., a working password or private key) that is intended to limit public access. [no_leaked_credentials] 
A project MAY leak "sample" credentials for testing and unimportant databases, as long as they are not intended to limit public access.
No leaked credentials justification

By submitting this data about the project you agree to release it under at least the Community Data License Agreement – Permissive, Version 2.0. This means that a Data Recipient may share the Data, with or without modifications, so long as the Data Recipient makes available the text of this agreement with the shared Data. This agreement does not impose any restriction or obligations with respect to the use, modification, or sharing of Results. You retain copyright (if any), and the project license is unaffected.

You can use tools and AI systems to propose changes via a simple URL, such as https://www.bestpractices.dev/en/projects/13183/choose/edit?osps_ac_01_01_status=Met&osps_ac_01_01_justification=GitHub+enforced. See our automation proposals system for how to do that.

 
 Analysis0/8 ●
Static code analysis

Unknown required information, not enough for a badge.
Met
Unmet
N/A
?

At least one static code analysis tool (beyond compiler warnings and "safe" language modes) MUST be applied to any proposed major production release of the software before its release, if there is at least one FLOSS tool that implements this criterion in the selected language. [static_analysis] 
A static code analysis tool examines the software code (as source code, intermediate code, or executable) without executing it with specific inputs. For purposes of this criterion, compiler warnings and "safe" language modes do not count as static code analysis tools (these typically avoid deep analysis because speed is vital). Some static analysis tools focus on detecting generic defects, others focus on finding specific kinds of defects (such as vulnerabilities), and some do a combination. Examples of such static code analysis tools include cppcheck (C, C++), clang static analyzer (C, C++), SpotBugs (Java), FindBugs (Java) (including FindSecurityBugs), PMD (Java), Brakeman (Ruby on Rails), lintr (R), goodpractice (R), Coverity Quality Analyzer, SonarQube, Codacy, and HP Enterprise Fortify Static Code Analyzer. Larger lists of tools can be found in places such as the Wikipedia list of tools for static code analysis, OWASP information on static code analysis, NIST list of source code security analyzers, and Wheeler's list of static analysis tools. If there are no FLOSS static analysis tools available for the implementation language(s) used, you may select 'N/A'.
Static analysis justification

Unknown required information, not enough for a badge.
Met
Unmet
N/A
?

It is SUGGESTED that at least one of the static analysis tools used for the static_analysis criterion include rules or approaches to look for common vulnerabilities in the analyzed language or environment. [static_analysis_common_vulnerabilities] 
Static analysis tools that are specifically designed to look for common vulnerabilities are more likely to find them. That said, using any static tools will typically help find some problems, so we are suggesting but not requiring this for the 'passing' level badge.
Static analysis common vulnerabilities justification

Unknown required information, not enough for a badge.
Met
Unmet
N/A
?

All medium and higher severity exploitable vulnerabilities discovered with static code analysis MUST be fixed in a timely way after they are confirmed. [static_analysis_fixed] 
A vulnerability is considered medium or higher severity if its Common Vulnerability Scoring System (CVSS) base qualitative score is medium or higher. In CVSS versions 2.0 through 3.1, this is equivalent to a CVSS score of 4.0 or higher. Projects may use the CVSS score as published in a widely-used vulnerability database (such as the National Vulnerability Database) using the most-recent version of CVSS reported in that database. Projects may instead calculate the severity themselves using the latest version of CVSS at the time of the vulnerability disclosure, if the calculation inputs are publicly revealed once the vulnerability is publicly known. Note that criterion vulnerabilities_fixed_60_days requires that all such vulnerabilities be fixed within 60 days of being made public.
Static analysis fixed justification

Unknown required information, not enough for a badge.
Met
Unmet
N/A
?

It is SUGGESTED that static source code analysis occur on every commit or at least daily. [static_analysis_often]
Static analysis often justification

Dynamic code analysis

Unknown required information, not enough for a badge.
Met
Unmet
?

It is SUGGESTED that at least one dynamic analysis tool be applied to any proposed major production release of the software before its release. [dynamic_analysis] 
A dynamic analysis tool examines the software by executing it with specific inputs. For example, the project MAY use a fuzzing tool (e.g., American Fuzzy Lop) or a web application scanner (e.g., OWASP ZAP or w3af). In some cases the OSS-Fuzz project may be willing to apply fuzz testing to your project. For purposes of this criterion the dynamic analysis tool needs to vary the inputs in some way to look for various kinds of problems or be an automated test suite with at least 80% branch coverage. The Wikipedia page on dynamic analysis and the OWASP page on fuzzing identify some dynamic analysis tools. The analysis tool(s) MAY be focused on looking for security vulnerabilities, but this is not required.
Dynamic analysis justification

Unknown required information, not enough for a badge.
Met
Unmet
N/A
?

It is SUGGESTED that if the software produced by the project includes software written using a memory-unsafe language (e.g., C or C++), then at least one dynamic tool (e.g., a fuzzer or web application scanner) be routinely used in combination with a mechanism to detect memory safety problems such as buffer overwrites. If the project does not produce software written in a memory-unsafe language, choose "not applicable" (N/A). [dynamic_analysis_unsafe] 
Examples of mechanisms to detect memory safety problems include Address Sanitizer (ASAN) (available in GCC and LLVM), Memory Sanitizer, and valgrind. Other potentially-used tools include thread sanitizer and undefined behavior sanitizer. Widespread assertions would also work.
Dynamic analysis unsafe justification

Unknown required information, not enough for a badge.
Met
Unmet
?

It is SUGGESTED that the project use a configuration for at least some dynamic analysis (such as testing or fuzzing) which enables many assertions. In many cases these assertions should not be enabled in production builds. [dynamic_analysis_enable_assertions] 
This criterion does not suggest enabling assertions during production; that is entirely up to the project and its users to decide. This criterion's focus is instead to improve fault detection during dynamic analysis before deployment. Enabling assertions in production use is completely different from enabling assertions during dynamic analysis (such as testing). In some cases enabling assertions in production use is extremely unwise (especially in high-integrity components). There are many arguments against enabling assertions in production, e.g., libraries should not crash callers, their presence may cause rejection by app stores, and/or activating an assertion in production may expose private data such as private keys. Beware that in many Linux distributions NDEBUG is not defined, so C/C++ assert() will by default be enabled for production in those environments. It may be important to use a different assertion mechanism or defining NDEBUG for production in those environments.
Dynamic analysis enable assertions justification

Unknown required information, not enough for a badge.
Met
Unmet
N/A
?

All medium and higher severity exploitable vulnerabilities discovered with dynamic code analysis MUST be fixed in a timely way after they are confirmed. [dynamic_analysis_fixed] 
If you are not running dynamic code analysis and thus have not found any vulnerabilities in this way, choose "not applicable" (N/A). A vulnerability is considered medium or higher severity if its Common Vulnerability Scoring System (CVSS) base qualitative score is medium or higher. In CVSS versions 2.0 through 3.1, this is equivalent to a CVSS score of 4.0 or higher. Projects may use the CVSS score as published in a widely-used vulnerability database (such as the National Vulnerability Database) using the most-recent version of CVSS reported in that database. Projects may instead calculate the severity themselves using the latest version of CVSS at the time of the vulnerability disclosure, if the calculation inputs are publicly revealed once the vulnerability is publicly known.
Dynamic analysis fixed justification


By submitting this data about the project you agree to release it under at least the Community Data License Agreement – Permissive, Version 2.0. This means that a Data Recipient may share the Data, with or without modifications, so long as the Data Recipient makes available the text of this agreement with the shared Data. This agreement does not impose any restriction or obligations with respect to the use, modification, or sharing of Results. You retain copyright (if any), and the project license is unaffected.

You can use tools and AI systems to propose changes via a simple URL, such as https://www.bestpractices.dev/en/projects/13183/choose/edit?osps_ac_01_01_status=Met&osps_ac_01_01_justification=GitHub+enforced. See our automation proposals system for how to do that.