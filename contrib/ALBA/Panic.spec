#
# spec file for package Panic
#
# Copyright (c) 2016 SUSE LINUX Products GmbH, Nuernberg, Germany.
#
# All modifications and additions to the file contributed by third parties
# remain the property of their copyright owners, unless otherwise agreed
# upon. The license for this file, and modifications and additions to the
# file, is the same license as for the pristine package itself (unless the
# license for the pristine package is not an Open Source License, in which
# case the license is the MIT License). An "Open Source License" is a
# license that conforms to the Open Source Definition (Version 1.9)
# published by the Open Source Initiative.

# Please submit bugfixes or comments via http://bugs.opensuse.org/
#

%define _modname panic 

Name:           Panic
Version:        5.5  
Release:        0
License:        GPL-3.0+
Summary:        Alarm System toolkit
Url:            http://www.tango-controls.org/community/projects/panic/
Group:          Productivity/Scientific/Other
Source:         %{_modname}-%{version}.tar.gz
BuildRoot:      %{_tmppath}/%{name}-%{version}-build
BuildArch:      noarch

BuildRequires:  python-devel
BuildRequires:  python-setuptools

Requires: python < 3
Requires: python-numpy
Requires: python-taurus
Requires: python-pytango
Requires: python-fandango

%description
PANIC Alarm System is a set of tools (api, Tango device server, user interface) that provides:
    Periodic evaluation of a set of conditions.
    Notification (email, sms, pop-up, speakers)
    Keep a log of what happened. (files, Tango Snapshots)
    Taking automated actions (Tango commands / attributes)
    Tools for configuration/visualization.


# ================================================================
# python-panic
# ================================================================

%package -n python-panic
Summary: 	Alarm System toolkit. Python module
Group:   	Development/Languages/Python

%description -n python-panic
This package provides the "panic" python module from the PANIC Alarm System toolkit

# ================================================================
# tangods-pyalarm
# ================================================================

%package -n tangods-pyalarm
Summary:        Alarm System toolkit. PyAlarm Tango Device Server
Group:          Development/Libraries
Requires:       python-panic
#TODO: we should find a better group for DSs

%description -n tangods-pyalarm
This package provides the PyAlarm Tango Device Server from the PANIC Alarm System toolkit




%prep
%setup -n %{_modname}-%{version}

%build


%install
python setup.py install --prefix=%{_prefix} --root=%{buildroot}


%files -n python-panic
%defattr(-,root,root)
%exclude %{python_sitelib}/%{_modname}/ds
%{python_sitelib}


%files -n tangods-pyalarm
%defattr(-,root,root)
%{python_sitelib}/%{_modname}/ds
%{_bindir}/*
