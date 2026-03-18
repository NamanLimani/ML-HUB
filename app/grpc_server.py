import grpc
import os
from concurrent import futures
import sys

# --- FIX: THE gRPC IMPORT PATH HACK ---
# Tell Python to include this 'app' folder in its search path 
# so the generated files can easily find each other.
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import federated_pb2
import federated_pb2_grpc

CHUNK_SIZE = 64 * 1024 # 64KB chunks to keep memory usage near zero

class FederatedHubServicer(federated_pb2_grpc.ModelTransferServicer):
    """
    This class fills in the blanks for the gRPC blueprint we designed.
    It handles the actual file reading and writing.
    """

    def DownloadModel(self , request , context):
        print(f"[gRPC] Edge node requested download for job {request.job_id}")
        file_path = f"app/model_registry/global_model_job_{request.job_id}.pt"

        if not os.path.exists(file_path):
            # If the file isn't there, we tell gRPC to send an error code
            context.set_code(grpc.StatusCode.NOT_FOUND)
            context.set_details("Model File not found in registry")
            return 
        
        # Open the file and yield it piece by piece
        with open(file_path , "rb") as f:
            while True:
                piece = f.read(CHUNK_SIZE)
                if len(piece) == 0:
                    break # End of file

                # Package the bytes into our Protobuf message and send it down the pipe
                yield federated_pb2.ModelChunk(
                    job_id = request.job_id ,
                    chunk_data = piece
                )
            
            print(f"[gPRC] Successfully streamed global model for job {request.job_id}")

    def UploadModel(self , request_iterator , context):
        job_id = None
        node_id = None
        file_path = None
        file_object = None

        print("[gPRC] Incoming edge model stream detected ....")

        try:
            # request_iterator is the incoming river of chunks from the edge node
            for chunk in request_iterator:
                # On the very first chunk, figure out who is sending this and open a file
                if file_object is None :
                    job_id = chunk.job_id
                    node_id = chunk.node_id

                    upload_dir = "app/uploaded_weights"
                    os.makedirs(upload_dir , exist_ok=True)
                    file_path = os.path.join(upload_dir , f"job_{job_id}_node_{node_id}.pt")
                    file_object = open(file_path , "wb")
                
                # Write the binary data directly to the hard drive as it arrives
                file_object.write(chunk.chunk_data)
            
            print(f"[gPRC] Successfully saved uploaded model from node {node_id} (job {job_id})")

            # Send a final success message back to the edge node
            return federated_pb2.UploadResponse(
                message=f"Model from node {node_id} successfully received by HUB.",
                success = True
            )

        except Exception as e:
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f"upload failed: {str(e)}")
            return federated_pb2.UploadResponse(message = "upload failed" , success=False)
        
        finally :
            if file_object:
                file_object.close()

def serve_grpc():
    """Starts the gRPC server on a dedicated port."""

    # Create a server with a thread pool to handle multiple edge nodes simultaneously
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))

    # Attach our custom logic to the server
    federated_pb2_grpc.add_ModelTransferServicer_to_server(FederatedHubServicer() , server)

    # Listen on port 50051
    server.add_insecure_port('[::]: 50051')
    server.start()
    print("[gPRC SERVER] Listening for binary streams on port 50051...")

    # Keep the server alive
    server.wait_for_termination()

if __name__ == "__main__":
    serve_grpc()





