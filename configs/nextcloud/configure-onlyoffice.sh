#!/bin/bash
# Configure ONLYOFFICE connector in Nextcloud
# This script should be run after Nextcloud has started

# Wait for Nextcloud to be ready
echo "Waiting for Nextcloud to be ready..."
sleep 10

# Check if ONLYOFFICE app is installed
if ! su -s /bin/bash www-data -c "php /var/www/html/occ app:list" | grep -q "onlyoffice:"; then
    echo "Installing ONLYOFFICE connector app..."
    su -s /bin/bash www-data -c "php /var/www/html/occ app:install onlyoffice" || true
fi

# Enable ONLYOFFICE app if not enabled
su -s /bin/bash www-data -c "php /var/www/html/occ app:enable onlyoffice" || true

# Configure ONLYOFFICE settings
# IMPORTANT: StorageUrl MUST have a trailing slash to avoid URL concatenation issues
echo "Configuring ONLYOFFICE settings..."

# EXTERNAL URL: Used by browsers to load ONLYOFFICE JavaScript
su -s /bin/bash www-data -c "php /var/www/html/occ config:app:set onlyoffice DocumentServerUrl --value='${ONLYOFFICE_URL:-http://localhost:18082}'"

# INTERNAL URL: Used by Nextcloud server to communicate with ONLYOFFICE
su -s /bin/bash www-data -c "php /var/www/html/occ config:app:set onlyoffice DocumentServerInternalUrl --value='${ONLYOFFICE_INTERNAL_URL:-http://onlyoffice}'"

# STORAGE URL: Used by ONLYOFFICE to callback to Nextcloud (MUST have trailing slash!)
su -s /bin/bash www-data -c "php /var/www/html/occ config:app:set onlyoffice StorageUrl --value='${NEXTCLOUD_INTERNAL_URL:-http://nextcloud/}'"

# JWT Secret: Must match ONLYOFFICE Document Server's JWT_SECRET
su -s /bin/bash www-data -c "php /var/www/html/occ config:app:set onlyoffice jwt_secret --value='${ONLYOFFICE_JWT_SECRET:-auditcaseos-onlyoffice-secret}'"

# JWT Header
su -s /bin/bash www-data -c "php /var/www/html/occ config:app:set onlyoffice jwt_header --value='Authorization'"

echo "ONLYOFFICE configuration complete!"

# Verify configuration
echo ""
echo "Current ONLYOFFICE configuration:"
su -s /bin/bash www-data -c "php /var/www/html/occ config:list onlyoffice"
