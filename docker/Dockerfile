FROM nginx
CMD ["mkdir", "-p", "/var/www/my-company.com"]
CMD ["mkdir", "-p", "/etc/nginx/my-company.com"]

COPY nginx.conf /etc/nginx/nginx.conf
COPY index.html /var/www/my-company.com/index.html

CMD exec nginx -g 'daemon off;'