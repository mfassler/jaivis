
# Copyright 2009, Mark Fassler

# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, version 2 of the License.

import vtk

class create2dRectangle:
    def __init__ (self, xmin, ymin, xmax, ymax):
        self.pts = vtk.vtkPoints()
        self.pts.InsertPoint(0, xmin, ymin, 0)
        self.pts.InsertPoint(1, xmax, ymin, 0)
        self.pts.InsertPoint(2, xmax, ymax, 0)
        self.pts.InsertPoint(3, xmin, ymax, 0)
        self.rect = vtk.vtkCellArray()
        self.rect.InsertNextCell(4)
        self.rect.InsertCellPoint(0)
        self.rect.InsertCellPoint(1)
        self.rect.InsertCellPoint(2)
        self.rect.InsertCellPoint(3)
        self.selectRect = vtk.vtkPolyData()
        self.selectRect.SetPoints(self.pts)
        self.selectRect.SetPolys(self.rect)
        self.mapper = vtk.vtkPolyDataMapper2D()
        self.mapper.SetInput(self.selectRect)
        self.actor = vtk.vtkActor2D()
        self.actor.SetMapper(self.mapper)
        rprop = self.actor.GetProperty()
        rprop.SetColor(1, 1, 1)
        rprop.SetOpacity (0.4)

