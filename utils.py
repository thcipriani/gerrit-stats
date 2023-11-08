def make_safe_filename(repo_path):
    return ''.join(
        c if c.isalnum() or c in ['-', '_']
        else '_'
        for c in repo_path.encode(
            'ascii', 'xmlcharrefreplace').decode()
    )
