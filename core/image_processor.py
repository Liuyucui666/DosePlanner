"""
医学图像处理器

负责加载、预处理和显示CT图像。
支持DICOM和NIfTI格式。
"""

import numpy as np
from pathlib import Path
from typing import Dict, Any, Optional, Tuple, List, Union

import SimpleITK as sitk


class ImageProcessor:
    """医学图像处理器"""

    def __init__(self):
        """初始化图像处理器"""
        self._image_data = None

    def load_image(self, filepath: Union[str, Path]) -> Dict[str, Any]:
        """
        加载医学图像

        支持DICOM系列和NIfTI格式

        Args:
            filepath: 图像文件路径

        Returns:
            图像数据字典，包含：
                - 'array': NumPy数组 (z, y, x)
                - 'spacing': 体素间距 (mm)
                - 'origin': 图像原点坐标
                - 'direction': 方向矩阵
        """
        filepath = Path(filepath)

        if not filepath.exists():
            raise FileNotFoundError(f"图像文件未找到: {filepath}")

        # 根据文件扩展名选择加载方式
        ext = filepath.suffix.lower()
        if ext == ".dcm" or filepath.is_dir():
            return self._load_dicom(filepath)
        elif ext in (".nii", ".nii.gz", ".hdr", ".img"):
            return self._load_nifti(filepath)
        else:
            raise ValueError(f"不支持的文件格式: {ext}")

    def _load_dicom(self, filepath: Path) -> Dict[str, Any]:
        """
        加载DICOM图像

        Args:
            filepath: DICOM文件或目录路径

        Returns:
            图像数据字典
        """
        if filepath.is_dir():
            # 加载DICOM系列
            reader = sitk.ImageSeriesReader()
            dicom_names = reader.GetGDCMSeriesFileNames(str(filepath))
            if not dicom_names:
                raise ValueError(f"未找到DICOM文件: {filepath}")
            reader.SetFileNames(dicom_names)
            image = reader.Execute()
        else:
            # 加载单个DICOM文件
            image = sitk.ReadImage(str(filepath))

        return self._sitk_to_dict(image)

    def _load_nifti(self, filepath: Path) -> Dict[str, Any]:
        """
        加载NIfTI图像

        Args:
            filepath: NIfTI文件路径

        Returns:
            图像数据字典
        """
        image = sitk.ReadImage(str(filepath))
        return self._sitk_to_dict(image)

    def _sitk_to_dict(self, image: Any) -> Dict[str, Any]:
        """
        将SimpleITK图像转换为字典

        Args:
            image: SimpleITK图像对象

        Returns:
            图像数据字典
        """
        # 转换为NumPy数组
        array = sitk.GetArrayFromImage(image)

        # 获取元数据
        spacing = image.GetSpacing()
        origin = image.GetOrigin()
        direction = np.array(image.GetDirection()).reshape(3, 3)

        return {
            "array": array,
            "spacing": spacing,
            "origin": origin,
            "direction": direction,
            "size": image.GetSize(),
            "dimension": image.GetDimension(),
        }

    def get_slice(
        self,
        image_data: Dict[str, Any],
        axis: str = "axial",
        slice_index: int = 0,
    ) -> np.ndarray:
        """
        获取指定方向的切片

        Args:
            image_data: 图像数据字典
            axis: 切片方向 ('axial', 'coronal', 'sagittal')
            slice_index: 切片索引

        Returns:
            2D切片数组
        """
        array = image_data["array"]

        if axis == "axial":
            return array[slice_index, :, :]
        elif axis == "coronal":
            return array[:, slice_index, :]
        elif axis == "sagittal":
            return array[:, :, slice_index]
        else:
            raise ValueError(f"不支持的切片方向: {axis}")

    def apply_window_level(
        self,
        image_array: np.ndarray,
        window_width: float = 400.0,
        window_level: float = 40.0,
    ) -> np.ndarray:
        """
        应用窗宽窗位调整

        Args:
            image_array: 原始图像数组
            window_width: 窗宽
            window_level: 窗位

        Returns:
            调整后的图像数组 (0-255)
        """
        # 计算窗宽窗位范围
        lower = window_level - window_width / 2.0
        upper = window_level + window_width / 2.0

        # 应用窗宽窗位
        windowed = np.clip(image_array, lower, upper)

        # 归一化到0-255
        if upper > lower:
            windowed = (windowed - lower) / (upper - lower) * 255.0

        return windowed.astype(np.uint8)

    def resample_image(
        self,
        image_data: Dict[str, Any],
        new_spacing: Tuple[float, float, float],
        interpolator: int = 1,
    ) -> Dict[str, Any]:
        """
        重采样图像到新的体素间距

        Args:
            image_data: 图像数据字典
            new_spacing: 新的体素间距 (mm)
            interpolator: 插值器类型 (1=线性, 2=样条, 3=最近邻)

        Returns:
            重采样后的图像数据
        """
        # 重建SimpleITK图像
        image = self._dict_to_sitk(image_data)

        # 创建重采样器
        resampler = sitk.ResampleImageFilter()
        resampler.SetOutputSpacing(new_spacing)
        resampler.SetSize([
            int(image_data["size"][0] * image_data["spacing"][0] / new_spacing[0]),
            int(image_data["size"][1] * image_data["spacing"][1] / new_spacing[1]),
            int(image_data["size"][2] * image_data["spacing"][2] / new_spacing[2]),
        ])
        resampler.SetOutputOrigin(image.GetOrigin())
        resampler.SetOutputDirection(image.GetDirection())
        resampler.SetInterpolator(interpolator)

        # 执行重采样
        resampled_image = resampler.Execute(image)

        return self._sitk_to_dict(resampled_image)

    def _dict_to_sitk(self, image_data: Dict[str, Any]) -> Any:
        """
        将图像数据字典转换为SimpleITK图像

        Args:
            image_data: 图像数据字典

        Returns:
            SimpleITK图像对象
        """
        image = sitk.GetImageFromArray(image_data["array"])
        image.SetSpacing(image_data["spacing"])
        image.SetOrigin(image_data["origin"])
        image.SetDirection(image_data["direction"].flatten().tolist())

        return image

    def register_images(
        self,
        fixed_image_data: Dict[str, Any],
        moving_image_data: Dict[str, Any],
    ) -> Tuple[Dict[str, Any], np.ndarray]:
        """
        图像配准

        Args:
            fixed_image_data: 参考图像数据
            moving_image_data: 待配准图像数据

        Returns:
            transformed_image: 配准后的图像数据
            transform_matrix: 变换矩阵
        """
        # 重建SimpleITK图像
        fixed_image = self._dict_to_sitk(fixed_image_data)
        moving_image = self._dict_to_sitk(moving_image_data)

        # 创建配准器
        registration_method = sitk.ImageRegistrationMethod()

        # 设置相似性度量
        registration_method.SetMetricAsMattesMutualInformation(
            numberOfHistogramBins=50
        )

        # 设置优化器
        registration_method.SetOptimizerAsGradientDescent(
            learningRate=1.0,
            numberOfIterations=100,
            convergenceMinimumValue=1e-6,
            convergenceWindowSize=10,
        )

        # 设置初始变换
        initial_transform = sitk.CenteredTransformInitializer(
            fixed_image,
            moving_image,
            sitk.Euler3DTransform(),
        )
        registration_method.SetInitialTransform(initial_transform)

        # 执行配准
        final_transform = registration_method.Execute(
            sitk.Cast(fixed_image, sitk.sitkFloat32),
            sitk.Cast(moving_image, sitk.sitkFloat32),
        )

        # 应用变换
        resampler = sitk.ResampleImageFilter()
        resampler.SetReferenceImage(fixed_image)
        resampler.SetInterpolator(sitk.sitkLinear)
        resampler.SetDefaultPixelValue(0)
        resampler.SetTransform(final_transform)

        transformed_image = resampler.Execute(moving_image)

        # 提取变换矩阵
        transform_matrix = np.array(final_transform.GetMatrix()).reshape(3, 3)

        return self._sitk_to_dict(transformed_image), transform_matrix

    def normalize_image(self, image_array: np.ndarray) -> np.ndarray:
        """
        归一化图像到0-1范围

        Args:
            image_array: 原始图像数组

        Returns:
            归一化后的图像数组
        """
        min_val = np.min(image_array)
        max_val = np.max(image_array)

        if max_val - min_val < 1e-10:
            return np.zeros_like(image_array)

        return (image_array - min_val) / (max_val - min_val)

    def standardize_image(self, image_array: np.ndarray) -> np.ndarray:
        """
        标准化图像（零均值，单位方差）

        Args:
            image_array: 原始图像数组

        Returns:
            标准化后的图像数组
        """
        mean = np.mean(image_array)
        std = np.std(image_array)

        if std < 1e-10:
            return np.zeros_like(image_array)

        return (image_array - mean) / std

    def get_image_statistics(self, image_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        获取图像统计信息

        Args:
            image_data: 图像数据字典

        Returns:
            统计信息字典
        """
        array = image_data["array"]

        return {
            "shape": array.shape,
            "spacing": image_data["spacing"],
            "origin": image_data["origin"],
            "dtype": str(array.dtype),
            "min": float(np.min(array)),
            "max": float(np.max(array)),
            "mean": float(np.mean(array)),
            "std": float(np.std(array)),
            "percentile_5": float(np.percentile(array, 5)),
            "percentile_95": float(np.percentile(array, 95)),
        }

    def convert_to_hu(self, image_data: Dict[str, Any]) -> np.ndarray:
        """
        转换为CT值(Hounsfield Units)

        Args:
            image_data: 图像数据字典

        Returns:
            CT值数组
        """
        image = self._dict_to_sitk(image_data)

        # 检查是否有RescaleSlope和RescaleIntercept
        if image.HasMetaDataKey("0028|1052") and image.HasMetaDataKey("0028|1053"):
            intercept = float(image.GetMetaData("0028|1052"))
            slope = float(image.GetMetaData("0028|1053"))
            hu_array = sitk.GetArrayFromImage(image) * slope + intercept
            return hu_array
        else:
            # 如果没有DICOM元数据，假设已经是HU
            return sitk.GetArrayFromImage(image)

    def extract_contour(
        self,
        image_array: np.ndarray,
        level: float = 0.0,
    ) -> List[np.ndarray]:
        """
        提取等值线（用于勾画轮廓）

        Args:
            image_array: 2D或3D图像数组
            level: 等值线值

        Returns:
            等值线点列表
        """
        try:
            from skimage import measure

            if image_array.ndim == 2:
                contours = measure.find_contours(image_array, level)
                return [c for c in contours]
            elif image_array.ndim == 3:
                # 提取每一层的等值线
                all_contours = []
                for i in range(image_array.shape[0]):
                    contours = measure.find_contours(image_array[i], level)
                    for contour in contours:
                        # 添加层索引作为z坐标
                        contour_3d = np.column_stack([
                            contour[:, 0],
                            contour[:, 1],
                            np.full(len(contour), i),
                        ])
                        all_contours.append(contour_3d)
                return all_contours
            else:
                raise ValueError(f"不支持的数组维度: {image_array.ndim}")
        except ImportError:
            raise ImportError("skimage is required for contour extraction")