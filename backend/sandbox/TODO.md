## Commands:
(From Root)

### Compiler
Docker build image: 
docker build -f backend/sandbox/Dockerfile.compiler -t compiler-image backend/sandbox/

Docker run container: 
docker run --rm -v $(pwd)/backend/sandbox/tmp/test:/workspace --memory=256m --network=none --pids-limit=50 compiler-image sh /scripts/compile.sh {CLASS_NAME}

### Runner
Docker build image:
docker

Docker run container:
docker run --rm -v $(pwd)/backend/sandbox/tmp/test:/workspace --memory=256m --network=none --pids-limit=50 runner-image sh /scripts/run.sh {CLASS_NAME} > $(pwd)/backend/sandbox/tmp/test/out/output.txt 2> $(pwd)/backend/sandbox/tmp/test/out/errors.txt

# TODO
- Implement them in python
- Implement the job queue interface
