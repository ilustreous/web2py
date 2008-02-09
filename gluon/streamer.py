def streamer(file,chunk_size=10**6):
    while 1:
        data=file.read(chunk_size)
        if not data: return
        else: yield data
