### Custom Nginx Docker Image <a name="custom_nginx"></a>
We will create a custom Nginx Docker image with the following configs:
- custom [nginx.conf](nginx.conf)
- custom html

[Dockerfile](Dockerfile) does a few things: make new dirs, copy files from our local host to a new image, and then start a nginx service.
```
FROM nginx
CMD ["mkdir", "-p", "/var/www/my-company.com"]
CMD ["mkdir", "-p", "/etc/nginx/my-company.com"]

COPY nginx.conf /etc/nginx/nginx.conf
COPY index.html /var/www/my-company.com/index.html

CMD exec nginx -g 'daemon off;'
```

Let's build and run a new Nginx image:
```
# build a container image using Dockerfile in the current dir by passing "."
$ docker build -t hasakura12/nginx-reverse-proxy .

# let's map host port 8080 and 8081 to a container port 8080 and 8081, and run a container in background
$ docker run \
  --name nginx-reverse-proxy \
  --rm \
  -d \
  -p 8080:8080 \
  -p 8081:8081 \
  hasakura12/nginx-reverse-proxy

# hit the Nginx server through port 8081
$ curl localhost:8081
```
and you should get a response:
```
Active connections: 1
server accepts handled requests
 6 6 6
Reading: 0 Writing: 1 Waiting: 0
```

### Custom Nginx Docker Image using docker-compose <a name="nginx_docker_compose"></a>
#### Prerequisite: docker-compose cli is installed

We could always run a docker container by the above
```
docker run \
  --name nginx-reverse-proxy \
  --rm \
  -d \
  -p 8080:8080 \
  -p 8081:8081 \
  hasakura12/nginx-reverse-proxy
```
But we could store these arguments in `docker-compose.yaml` file so we could maintain different configurations of different docker images.

[docker-compose.yaml](docker-compose.yaml) does that exactly: mapping host to container port, specifying docker image, etc.
```
version: '3'
services:
  nginx-reverse-proxy:
      image: hasakura12/nginx-reverse-proxy:latest
      container_name: nginx-reverse-proxy
      ports:
          - 8080:8080
          - 8081:8081
      restart: always
```

All you need to do is simply run:
```
docker-compose up -d
```

If you want to stop the container, run:
```
docker-compose down
```


#### Extra: passing commands to docker run command
```
docker run \
  -d \
  --name nginx-reverse-proxy \
  nginx-reverse-proxy \
  /bin/bash \
  -c "echo hello; exec nginx -g 'daemon off;'"
```

### Push custom Nginx Docker image to your Dockerhub public repo
```
# tag existing image "hasakura12/nginx-reverse-proxy" as "hasakura12/nginx-reverse-proxy:1.00" (DOCKERHUB_USERNAME/REPO_NAME:TAG_VERSION)
$ docker tag hasakura12/nginx-reverse-proxy hasakura12/nginx-reverse-proxy:1.00

# login to dockerhub
$ docker login

$ docker push hasakura12/nginx-reverse-proxy:1.00
```