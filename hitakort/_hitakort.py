import json
import re
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

from hitakort.defaults import CWD, HIT_REGEX


class HitaKort:
    """A class to manage a 6x6 grid heatmap, track hits, and generate visualizations.

    This class allows inputting grid points, tracking hit counts, and generating
    both data and image representations of the heatmap.

    Args:
        file_path (Path): Path to the JSON file for storing hit data.
            Can be a directory or a file path.
            Defaults to "./heatmap_data.json" in the current directory.
        grid_size (int): Size of the grid (6x6). Defaults to 6.
        override_size (bool): Whether to override the grid size if the persisted data size is different.
            Defaults to True.

    Attributes:
        grid (dict[str, int]): Dictionary to store hit counts for each grid point.
        size (int): Size of the grid.
        file_path (Path): Path to the JSON file for storing hit data.
    """

    def __init__(self, file_path: Path = CWD, grid_size: int = 6, override_size: bool = True) -> None:
        if not file_path.suffix:
            file_path = file_path / "heatmap_data.json"

        file_path.parent.mkdir(parents=True, exist_ok=True)
        if not file_path.exists():
            file_path.write_text("{}")

        self.grid: dict[str, int] = {}
        self.size: int = grid_size
        self.file_path: Path = file_path
        self._initialize_grid()
        self._load_data(override_size=override_size)

    def _initialize_grid(self) -> None:
        """Initialize the grid with zero hits for all points."""
        for row in range(1, self.size + 1):
            for col in range(self.size):
                point = f"{self._index_to_column(col)}{row}"
                self.grid[point] = 0

    @staticmethod
    def _index_to_column(index: int) -> str:
        """Convert a 0-based index to an Excel-style column label.

        Args:
            index (int): 0-based index to convert.

        Returns:
            str: Excel-style column label (e.g., 0 -> 'A', 25 -> 'Z', 26 -> 'AA').
        """
        result = ""
        index += 1  # Convert to 1-based index
        while index > 0:
            index -= 1
            result = chr(65 + (index % 26)) + result
            index = index // 26
        return result

    def _load_data(self, override_size: bool) -> None:
        """Load hit data from the JSON file if it exists.

        Args:
            override_size (bool): Whether to override the grid size if the persisted data size is different

        Raises:
            ValueError: If the grid data size does not match the expected size.
        """
        if self.file_path.exists() and (grid_data := json.loads(self.file_path.read_text())):
            if override_size or len(grid_data) == self.size**2:
                self.grid = grid_data
                self.size = int(len(grid_data) ** 0.5)
            else:
                raise ValueError("Persisted grid data size does not match the expected size")

    def _save_data(self) -> None:
        """Save hit data to the JSON file."""
        self.file_path.write_text(json.dumps(self.grid))

    def input_hit(self, point: str) -> None:
        """Record a hit for the given grid point.

        Args:
            point (str): Grid point in various formats (e.g., 'a1', 'A1', '1a', '1A', 'AAZ123', '123AAZ').

        Raises:
            ValueError: If the input point is invalid or out of the grid's range.
        """
        normalized_point = self._normalize_point(point)
        if normalized_point not in self.grid:
            raise ValueError(f"Point out of range: {point}")
        self.grid[normalized_point] += 1
        self._save_data()

    def _normalize_point(self, point: str) -> str:
        """Normalize the input point to the standard format (e.g., 'a1', 'aaz123').

        Args:
            point (str): Input point in various formats (e.g., 'A1', '1a', 'AAZ123', '123AAZ').

        Returns:
            str: Normalized point with letters first (uppercase) followed by numbers.

        Raises:
            ValueError: If the input point is invalid.
        """
        match = re.match(HIT_REGEX, point)

        if not match:
            raise ValueError(f"Invalid point format: {point}")

        groups = match.groupdict()
        if groups["letters"]:
            return f"{groups['letters'].upper()}{groups['numbers']}"
        else:
            return f"{groups['letters_second'].upper()}{groups['numbers_first']}"

    def generate_heatmap_data(self) -> list[list[int]]:
        """Generate a 2D list representing the heatmap data.

        Returns:
            list[list[int]]: 2D list of hit counts.
        """
        return [
            [self.grid[f"{self._index_to_column(col)}{row + 1}"] for col in range(self.size)]
            for row in range(self.size)
        ]

    def generate_heatmap_image(self) -> Image.Image:
        """Generate a heatmap image.

        Returns:
            Image.Image: A Pillow Image object representing the heatmap.
        """
        heatmap_data = np.array(self.generate_heatmap_data())
        max_value = np.max(heatmap_data)

        # Calculate the largest multiple of grid size that fits within 1024x1024
        img_size = min(1024, self.size * (1024 // self.size))

        # Resize the heatmap data to the calculated size
        resized_data = heatmap_data.repeat(img_size // self.size, axis=0).repeat(img_size // self.size, axis=1)

        # Normalize the data and convert to RGB
        normalized_data = resized_data / max_value if max_value > 0 else resized_data
        rgb_data = np.zeros((img_size, img_size, 3), dtype=np.uint8)
        rgb_data[..., 0] = 255  # Red channel
        rgb_data[..., 1] = rgb_data[..., 2] = 255 - (normalized_data * 255).astype(np.uint8)

        # Create image from the array
        img = Image.fromarray(rgb_data)

        # Add grid lines if the size is 1024x1024 or smaller
        if img_size <= 1024:
            img_with_grid = self._add_grid_lines(img)
            return img_with_grid

        return img

    def _add_grid_lines(self, img: Image.Image) -> Image.Image:
        """Add grid lines to the image.

        Args:
            img (Image.Image): The input image.

        Returns:
            Image.Image: The image with grid lines added.
        """
        draw = ImageDraw.Draw(img)
        step = img.width // self.size
        for i in range(1, self.size):
            line_position = i * step
            draw.line([(line_position, 0), (line_position, img.height)], fill=(0, 0, 0), width=1)
            draw.line([(0, line_position), (img.width, line_position)], fill=(0, 0, 0), width=1)
        return img

    @staticmethod
    def _get_color(value: int, max_value: int) -> tuple[int, int, int]:
        """Get the color for a cell based on its value.

        Args:
            value (int): Hit count for the cell.
            max_value (int): Maximum hit count in the grid.

        Returns:
            tuple[int, int, int]: RGB color tuple.
        """
        if max_value == 0:
            return (255, 255, 255)  # White for no hits
        intensity = int(255 * (value / max_value))
        return (255, 255 - intensity, 255 - intensity)  # White to Red gradient

    def generate_ascii_heatmap(self) -> str:
        """Generate a coloured ASCII art representation of the heatmap.

        Returns:
            str: A string containing the ASCII art heatmap with ANSI color codes.
        """
        heatmap_data = self.generate_heatmap_data()
        max_value = max(max(row) for row in heatmap_data)

        ascii_map = []
        for row in heatmap_data:
            ascii_row = []
            for value in row:
                color_code = self._get_ascii_color(value, max_value)
                ascii_row.append(f"{color_code}██\033[0m")  # Use Unicode full block
            ascii_map.append("".join(ascii_row))

        # Add column labels
        col_labels = "   " + "".join(f"{self._index_to_column(i):2}" for i in range(self.size))

        # Add row labels and construct the final map
        labelled_map = [col_labels] + [f"{i + 1:2} " + row for i, row in enumerate(ascii_map)]

        return "\n".join(labelled_map)

    @staticmethod
    def _get_ascii_color(value: int, max_value: int) -> str:
        """Get the ANSI color code for a cell based on its value.

        Args:
            value (int): Hit count for the cell.
            max_value (int): Maximum hit count in the grid.

        Returns:
            str: ANSI color code.
        """
        if max_value == 0:
            return "\033[38;5;255m"  # White for no hits

        r, g, b = HitaKort._get_color(value, max_value)

        # Convert RGB to the closest ANSI 256-color code
        ansi_code = 16 + (36 * round(r / 255 * 5)) + (6 * round(g / 255 * 5)) + round(b / 255 * 5)
        return f"\033[38;5;{ansi_code}m"
