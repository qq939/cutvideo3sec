import unittest
import os
import sys
from unittest.mock import patch, MagicMock
from io import BytesIO

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import app

class TestVideoCutApp(unittest.TestCase):
    def setUp(self):
        self.client = app.app.test_client()
        self.app = app.app
        self.app.config['TESTING'] = True
        
    @patch('app.VideoFileClip')
    @patch('requests.post')
    def test_upload_and_cut(self, mock_post, mock_video_clip):
        # Mock VideoFileClip
        mock_clip_instance = MagicMock()
        mock_clip_instance.duration = 10 # 10 seconds video
        
        # Mock subclip to return a clip that can write_videofile
        mock_subclip = MagicMock()
        
        def side_effect_write(*args, **kwargs):
            # Create a dummy file at the path
            path = args[0]
            with open(path, 'wb') as f:
                f.write(b'dummy segment content')
        
        mock_subclip.write_videofile.side_effect = side_effect_write
        mock_clip_instance.subclip.return_value = mock_subclip
        
        mock_video_clip.return_value = mock_clip_instance
        
        # Mock requests.post
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {'message': 'success'}
        
        # Create a dummy video file
        data = {
            'video': (BytesIO(b'fake video content'), 'test.mp4')
        }
        
        response = self.client.post('/upload_and_cut', data=data, content_type='multipart/form-data')
        
        self.assertEqual(response.status_code, 200)
        self.assertIn('processed', response.json['status'])
        
        # Verify calls
        # Should call subclip 4 times: 0-3, 3-6, 6-9, 9-10
        # Wait, if duration is 10, steps: 0, 3, 6, 9.
        # 0-3, 3-6, 6-9, 9-10.
        # So 4 calls to subclip.
        self.assertEqual(mock_clip_instance.subclip.call_count, 4)
        
        # Verify posts
        self.assertEqual(mock_post.call_count, 4)
        # Check target URL
        args, kwargs = mock_post.call_args
        self.assertEqual(args[0], "http://videocut.dimond.top/overall")
        
    def test_upload_no_file(self):
        response = self.client.post('/upload_and_cut', data={}, content_type='multipart/form-data')
        self.assertEqual(response.status_code, 400)

    def test_index_page(self):
        """Test that the index page returns 200 OK"""
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'html', response.data.lower())

if __name__ == '__main__':
    unittest.main()
