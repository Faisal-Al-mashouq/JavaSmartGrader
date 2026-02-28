## Commands:
(From Root)

### Compiler
Docker build image: 
docker build -f backend/sandbox/Dockerfile.compiler -t compiler-image backend/sandbox/

Docker run container: 
docker run --rm -v $(pwd)/backend/sandbox/tmp/test:/workspace --memory=256m --network=none --pids-limit=50 compiler-image sh /scripts/compile.sh {CLASS_NAME}

### Executer
Docker build image:
docker build -f backend/sandbox/Dockerfile.executer -t executer-image backend/sandbox/

Docker run container:
docker run --rm -v $(pwd)/backend/sandbox/tmp/test:/workspace --memory=256m --network=none --pids-limit=50 --read-only executer-image sh /scripts/execute.sh {CLASS_NAME} > $(pwd)/backend/sandbox/tmp/test/out/output.txt 2> $(pwd)/backend/sandbox/tmp/test/out/errors.txt

# TODO
- ~~Implement them in python~~ - Done
- ~~Implement the job queue interface~~ - Done
- ~~Add graceful shutdown handling~~ - Done
- ~~Split sandbox_worker.py into modular files (helpers, jobs, schemas, test_jobs)~~ - Done
- ~~Add proper Pydantic schemas for execution outputs~~ - Done
- ~~Implement temporary file-based result saving~~ - Done
- ~~Clean up duplicate imports and constants across modules~~ - Done
- ~~Add auto initialization for Docker images~~ - Done
- ~~Build and test Docker images end-to-end~~ - Done
- Implement result saving logic (Redis/database persistence)
