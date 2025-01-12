#!/usr/bin/perl
use strict;
use warnings;
use POSIX qw(locale_h);

# Bestimme das Protokoll (http oder https)
my $request_scheme;
if ($ENV{"HTTP_FRONT_END_HTTPS"} && $ENV{"HTTP_FRONT_END_HTTPS"} eq "on") {
    $request_scheme = "https";
} elsif ($ENV{"REQUEST_SCHEME"}) {
    $request_scheme = $ENV{"REQUEST_SCHEME"};
} else {
    $request_scheme = "http";
}

print "Content-type: text/html", "\n\n";
# HTML-Ausgabe
print "<html><head></head><body>\n";
print "<font size=+1>Environment</font><br/>\n";

# Schleife durch Umgebungsvariablen
foreach my $key (sort keys %ENV) {
    print "<b>" . sprintf("%20s", $key) . "</b>: " . $ENV{$key} . "<br/>\n";
}

# Access-Control-Allow-Origin
if ($ENV{"HTTP_ORIGIN"}) {
    print "Access-Control-Allow-Origin: " . $ENV{"HTTP_ORIGIN"} . "<br/>\n";
} else {
    print "Access-Control-Allow-Origin: $request_scheme://" . $ENV{"HTTP_HOST"} . "<br/>\n";
}

# Bevorzugte Kodierung
my $locale = setlocale(LC_CTYPE);
print "Preferred encoding: $locale\n";

print "</body></html>\n";
