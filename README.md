# Container for testing SAML IdP SP interaction using mod-auth-mellon

This is a container that can be used in Kubernetes to test IdP (keycloak)  
and SP (mod-auth-mellon) SAML interaction.  
It also contains a lot of proxy_<protocol> apache2 modules so it can be used  
for reverse proxies handlingen SAML SSO.

## Example Setup configuring mod_auth_mellon with Keycloak on Kubernetes

Slightly adapted from https://www.keycloak.org/securing-apps/mod-auth-mellon

There are two hosts involved:

* The host on which Keycloak is running, which will be referred to as $idp_host because Keycloak is a SAML identity provider (IdP).
* The host on which the web application is running, which will be referred to as $sp_host. In SAML an application using an IdP is called a service provider (SP). This is set up on Kubernetes.

For installed packages see [Dockerfile](Dockerfile).

### Configuring the Mellon Service Provider

Configuration files for Apache add-on modules are located in the `/etc/apache2/conf-enabled` directory and have a file name extension of .conf. You need to create the `/etc/apache2/conf-enabled/mellon.conf` file and place Mellon’s configuration directives in it. The eseast way to do this is to create a config map and mount `/etc/apache2/conf-enabled/mellon.conf` from there.

Mellon’s configuration directives can roughly be broken down into two classes of information:

* Which URLs to protect with SAML authentication
* What SAML parameters will be used when a protected URL is referenced.

Apache configuration directives typically follow a hierarchical tree structure in the URL space, which are known as locations. You need to specify one or more URL locations for Mellon to protect. You have flexibility in how you add the configuration parameters that apply to each location. You can either add all the necessary parameters to the location block or you can add Mellon parameters to a common location high up in the URL location hierarchy that specific protected locations inherit (or some combination of the two). Since it is common for an SP to operate in the same way no matter which location triggers SAML actions, the example configuration used here places common Mellon configuration directives in the root of the hierarchy and then specific locations to be protected by Mellon can be defined with minimal directives. This strategy avoids duplicating the same parameters for each protected location.

This example has just one protected location: https://$sp_host/private.

To configure the Mellon service provider, create the config map `etc-apache2-conf-enabled` and add a key `mellon.conf` with this content:
```apache
<VirtualHost *:80>
    ServerName https://$sp_host
</VirtualHost>
<Location / >
    MellonEnable info
    MellonEndpointPath /mellon/
    MellonSPMetadataFile /etc/apache2/saml2/sp-metadata.xml
    MellonSPPrivateKeyFile /etc/apache2/saml2/client-private-key.pem
    MellonSPCertFile /etc/apache2/saml2/client-cert.pem
    MellonIdPMetadataFile /etc/apache2/saml2/idp-metadata.xml
    MellonSecureCookie On
    MellonCookieSameSite none
 </Location>
 <Location /private >
    AuthType Mellon
    MellonEnable auth
    Require valid-user
#    ProxyPass "http://http-echo.default:8080/"
#    ProxyPassReverse  "http://http-echo.default:8080/"
 </Location>
```

The container does not use certificates or listens on port 443. Instead the ServerName forces Apache to use https internally by specifying this scheme.

It is assumed that this service is fronted with an Ingress that handles TLS.

For more options see the [mod-auth-mellon repository](https://github.com/latchset/mod_auth_mellon).

### Creating the Service Provider metadata

In SAML IdPs and SPs exchange SAML metadata, which is in XML format. The schema for the metadata is a standard, thus assuring participating SAML entities can consume each other’s metadata. You need:
* Metadata for the IdP that the SP utilizes
* Metadata describing the SP provided to the IdP

One of the components of SAML metadata is X509 certificates. These certificates are used for two purposes:
* Sign SAML messages so the receiving end can prove the message originated from the expected party.
* Encrypt the message during transport (seldom used because SAML messages typically occur on TLS-protected transports)

You can use your own certificates if you already have a Certificate Authority (CA) or you can generate a self-signed certificate. For simplicity in this example a self-signed certificate is used.  
Because Mellon’s SP metadata must reflect the capabilities of the installed version of mod_auth_mellon, must be valid SP metadata XML, and must contain an X509 certificate (whose creation can be obtuse unless you are familiar with X509 certificate generation) the most expedient way to produce the SP metadata is to use a tool included in the mod_auth_mellon package (mellon_create_metadata.sh). The generated metadata can always be edited later because it is a text file. The tool also creates your X509 key and certificate.

SAML IdPs and SPs identify themselves using a unique name known as an EntityID. To use the Mellon metadata creation tool you need:
* The EntityID, which is typically the URL of the SP, and often the URL of the SP where the SP metadata can be retrieved
* The URL where SAML messages for the SP will be consumed, which Mellon calls the MellonEndPointPath.

To create the SP metadata, use the following shell code. Execute the following in a shell in the running Pod:
```bash
cd /run/apache2
fqdn='$sp_host'
mellon_endpoint_url="https://${fqdn}/mellon"
mellon_entity_id="${mellon_endpoint_url}/metadata"
file_prefix="$(echo "$mellon_entity_id" | sed 's/[^A-Za-z.]/_/g' | sed 's/__*/_/g')"

mellon_create_metadata $mellon_entity_id $mellon_endpoint_url

#Output files:
#Private key:               #https_sp_host_mellon_metadata.key
#Certificate:               #https_sp_host_mellon_metadata.cert
#Metadata:                  #https_sp_host_mellon_metadata.xml
#
#Host:                      $sp_host
#
#Endpoints:
#SingleLogoutService:       https://$sp_host/mellon/#logout
#AssertionConsumerService:  https://$sp_host/mellon/#postResponse
```

Copy the data form the generated certificate, key and metadata to a config map `etc-apache2-saml2` with keys `client-cert.pem`, `client-private-key.pem`, and `sp-metadata.xml`. A key `idp-metadata.xml`  will be filled in with data from keycloak. This is available at `https://$idp_host/realms/$realm/protocol/saml/descriptor`. So `test_realm` if you follow this instructions exactly.

Create a deployment and mount `etc-apache2-conf-enabled` to `/etc/apache2/conf-enabled/mellon.conf` with subPath `mellon.conf`.  
Mount `etc-apache2-saml2` to `/etc/apache2/saml2`.

### Adding the Mellon Service Provider to the Keycloak Identity Provider

Keycloak supports multiple tenancy where all users, clients, and so on are grouped in what is called a realm. Each realm is independent of other realms. You can use an existing realm in your Keycloak, but this example shows how to create a new realm called test_realm and use that realm.

All these operations are performed using the Keycloak Admin Console. You must have the admin username and password for $idp_host to perform the following procedure.
* Open the Admin Console and log on by entering the admin username and password.  
After logging into the Admin Console, there will be an existing realm. When Keycloak is first set up a root realm, master, is created by default. Any previously created realms are listed in the upper left corner of the Admin Console in a drop-down list.
* From the realm drop-down list select `Add realm`.
* In the Name field type `test_realm` and click `Create`.

### Adding the Mellon Service Provider as a client of the realm

In Keycloak SAML SPs are known as clients. To add the SP we must be in the Clients section of the realm.
* Click the Clients menu item on the left and click the `Import client` button.
* In the `Resource file` field, provide the `sp_metadata.xml` file created above. Note you can not paste the XML you have to upload a file.  
Depending on where your browser is running you might have to copy the SP metadata from $sp_host to the machine on which your browser is running so the browser can find the file.
* Click `Save`

### Editing the Mellon SP client

Set important client configuration parameters:
* Ensure `Force POST Binding` is `On`.
* Add `paosResponse` to the `Valid Redirect URIs` list:
  * Copy the `postResponse` URL in `Valid Redirect URIs` and paste it into the empty add text fields just below the "+".
  * Change `postResponse` to `paosResponse`. (The paosResponse URL is needed for SAML ECP.)
* Click Save at the bottom.
  
Many SAML SPs determine authorization based on a user’s membership in a group. The Keycloak IdP can manage user group information but it does not supply the user’s groups unless the IdP is configured to supply it as a SAML attribute.

Configure the IdP to supply the user’s groups as a SAML attribute:
* Click the `Client scopes` tab of the client.
* Click the dedicated scope placed in the first row.  
  It follows the pattern `https://$sp-host/mellon/metadata-dedicated`
* In the Mappers page, click the `Configure New Mapper` or `Add mapper` button and select `By configuration`.
* From the list select `Group list`.
* Set Name to `group list`.
* Set the SAML attribute name to `groups`.
* Click Save.
