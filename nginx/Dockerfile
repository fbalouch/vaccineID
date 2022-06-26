# Ref: https://github.com/GoogleContainerTools/distroless/blob/main
# Start multi-stage build for nginx base image
FROM node:16 as build
WORKDIR /usr/local/vaccine-id
COPY spa .
RUN npm install --legacy-peer-deps
RUN npm run build --omit=dev

# Second stage for nginx
FROM nginx:1.21.6 as base

# Copy Angular build
COPY --from=build /usr/local/vaccine-id/dist/vaccine-id /usr/share/nginx/html

# Copy openapi spec
COPY openapi/spec.html /usr/share/nginx/html
COPY openapi/openapi.yaml /usr/share/nginx/html

# Copy nginx conf
COPY config/nginx.conf /etc/nginx/conf.d/default.conf

# Set working directory
WORKDIR /tmp
COPY config/openssl.conf .

# Create self-signed certificate
RUN openssl req -new -sha256 -newkey rsa:2048 -days 365 -nodes -x509 \
    -keyout /etc/nginx/conf.d/vaccine-id.example.com.key \
    -out /etc/nginx/conf.d/vaccine-id.example.com.crt -config openssl.conf && \
    chown 65533:65533 /etc/nginx/conf.d/vaccine-id.example.com.*

# Set time zone
# https://en.wikipedia.org/wiki/List_of_tz_database_time_zones
ARG TIME_ZONE=UTC

# Stage nginx dependencies 
RUN mkdir -p /opt/var/cache/nginx && \
    mkdir /opt/var/cache/nginx/client_temp && \
    mkdir /opt/var/cache/nginx/proxy_temp && \
    mkdir /opt/var/cache/nginx/fastcgi_temp && \
    mkdir /opt/var/cache/nginx/uwsgi_temp && \
    mkdir /opt/var/cache/nginx/scgi_temp && \
    cp -a --parents /usr/lib/nginx /opt && \
    cp -a --parents /usr/share/nginx /opt && \
    cp -a --parents /var/log/nginx /opt && \
    cp -aL --parents /var/run /opt && \
    cp -a --parents /etc/nginx /opt && \
    cp -a --parents /etc/passwd /opt && \
    cp -a --parents /etc/group /opt && \
    cp -a --parents /usr/sbin/nginx /opt && \
    cp -a --parents /usr/sbin/nginx-debug /opt && \
    cp -a --parents /lib/x86_64-linux-gnu/ld-* /opt && \
    cp -a --parents /lib/x86_64-linux-gnu/libpcre.so.* /opt && \
    cp -a --parents /lib/x86_64-linux-gnu/libz.so.* /opt && \
    cp -a --parents /lib/x86_64-linux-gnu/libc* /opt && \
    cp -a --parents /lib/x86_64-linux-gnu/libdl* /opt && \
    cp -a --parents /lib/x86_64-linux-gnu/libpthread* /opt && \
    cp -a --parents /lib/x86_64-linux-gnu/libcrypt* /opt && \
    cp -a --parents /usr/lib/x86_64-linux-gnu/libssl.so.* /opt && \
    cp -a --parents /usr/lib/x86_64-linux-gnu/libcrypto.so.* /opt && \
    cp -a --parents /usr/lib/x86_64-linux-gnu/libpcre2-8.so.* /opt && \
    cp /usr/share/zoneinfo/${TIME_ZONE:-ROC} /opt/etc/localtime && \
    touch /opt/var/run/nginx.pid && \
    chown 65533:65533 /opt/var/run/nginx.pid

# Final stage from distroless
FROM gcr.io/distroless/base-debian11

# Copy nginx dependencies from second stage
COPY --from=base /opt /

# Kubernetes runAsNonRoot requires USER to be numeric
USER 65533:65533

# Expose on port 443
EXPOSE 8443

# Container entrypoint
ENTRYPOINT ["nginx", "-g", "daemon off;"]