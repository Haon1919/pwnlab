<?php
# DVWA Configuration for BlaqLiq
# Security level starts at LOW for beginner scenarios

$_DVWA = array();
$_DVWA[ 'db_server' ]   = '127.0.0.1';
$_DVWA[ 'db_database' ] = 'dvwa';
$_DVWA[ 'db_user' ]     = 'dvwa';
$_DVWA[ 'db_password' ] = 'p@ssw0rd';
$_DVWA[ 'db_port']      = '3306';

$_DVWA[ 'default_security_level' ] = 'low';
$_DVWA[ 'default_phpids_level' ]   = 'disabled';
$_DVWA[ 'default_phpids_verbose' ] = 'false';
$_DVWA[ 'recaptcha_public_key' ]   = '';
$_DVWA[ 'recaptcha_private_key' ]  = '';

?>
