FROM debian:bookworm-slim

ENV DEBIAN_FRONTEND=noninteractive \
    APACHE_LOCK_DIR=/run/apache2 \
    APACHE_RUN_DIR=/run/apache2 \
	APACHE_PID_FILE=/run/apache2/apache2.pid \
	APACHE_RUN_USER=www-data \
	APACHE_RUN_GROUP=www-data \
	APACHE_LOG_DIR=/run/apache2

RUN apt-get update && apt-get -y full-upgrade && \
    apt-get install -y \
	apache2 apache2-data \
	libapache2-mod-auth-mellon && \
	a2enmod auth_mellon && a2enmod proxy && \
	mkdir -p /run/apache2 && chown -R www-data:www-data /run/apache2 && \
	ln -s /proc/self/fd/1 $APACHE_LOG_DIR/error.log && \
	ln -s /proc/self/fd/1 $APACHE_LOG_DIR/access.log
	
EXPOSE 80
USER www-data
CMD ["/usr/sbin/apache2", "-DFOREGROUND"]