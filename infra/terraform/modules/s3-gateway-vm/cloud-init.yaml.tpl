#cloud-config
package_update: true
packages:
  - docker.io

write_files:
  - path: /etc/s3proxy/s3proxy.conf
    permissions: "0600"
    content: |
      s3proxy.authorization=aws-v2-or-v4
      s3proxy.endpoint=http://0.0.0.0:9000
      s3proxy.identity=${s3_access_key}
      s3proxy.credential=${s3_secret_key}
      jclouds.provider=azureblob
      jclouds.identity=${storage_account_name}
      jclouds.credential=${storage_account_key}
      jclouds.endpoint=${blob_endpoint}
      jclouds.azureblob.auth=azureKey

runcmd:
  - mkdir -p /etc/s3proxy
  - systemctl enable docker
  - systemctl start docker
  - docker pull gaul/s3proxy:2.5.1
  - docker run -d --restart unless-stopped --name s3proxy -p 9000:9000 -v /etc/s3proxy/s3proxy.conf:/opt/s3proxy/conf/s3proxy.conf gaul/s3proxy:2.5.1
