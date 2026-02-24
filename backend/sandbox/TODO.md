## Commands:
(From Root)

### Compiler
Docker build image: 
docker build -f backend/sandbox/Dockerfile.compiler -t compiler-image backend/sandbox/

Docker run container: 
docker run --rm -v $(pwd)/backend/sandbox/tmp/test:/workspace --memory=256m --network=none --pids-limit=50 compiler-image sh /scripts/compile.sh {CLASS_NAME}

### Executer
Docker build image:
docker build -f backend/sandbox/Dockerfile.runner -t executer-image backend/sandbox/

Docker run container:
docker run --rm -v $(pwd)/backend/sandbox/tmp/test:/workspace --memory=256m --network=none --pids-limit=50 --read-only executer-image sh /scripts/execute.sh {CLASS_NAME} > $(pwd)/backend/sandbox/tmp/test/out/output.txt 2> $(pwd)/backend/sandbox/tmp/test/out/errors.txt

# TODO
- ~~Implement them in python~~ - Done
- ~~Implement the job queue interface~~ - Done
- ~~Add graceful shutdown handling~~ - Done
- Implement result saving logic (Redis/database persistence)
- Add unit tests for sandbox worker
- Add auto initialization for Docker images
- Build and test Docker images end-to-end
