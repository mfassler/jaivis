
# Copyright 2009, Mark Fassler

# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, version 2 of the License.

import logging
import vtk
from jv.jvPaths import *
import xml.etree.ElementTree as ET
import xml #for error handling
import os


vtkTypes = {}
vtkTypes['Mapper']      = ['DataSetMapper', 'PolyDataMapper']
vtkTypes['Algorithm']   = ['CylinderSource', 'SphereSource', 'CubeSource', 'DiskSource',
                           'ConeSource', 'UnstructuredGridReader', 'PolyDataReader', 
                           'TextureMapToPlane', 'TextureMapToSphere', 'ContourFilter',
                           'TransformTextureCoords', 'TransformPolyDataFilter',
                           'TransformFilter', 'ImplicitModeller', 
                           'Glyph3D', 'GlyphSource2D', 'ImplicitSum', 
                           'SampleFunction', 'PolyDataNormals']
vtkTypes['ImageReader'] = ['BMPReader']
vtkTypes['LinearTransform'] = ['Transform']
vtkTypes['Prop3D'] = ['Actor']
vtkTypes['ImplicitFunction'] = ['Plane', 'PerlinNoise']


def coordsFromString(string):
    coords = string.split(',')
    x = float(coords[0])
    y = float(coords[1])
    z = float(coords[2])
    return x, y, z

def str2floats(myString):
    return map(lambda x: float(x), myString.split(","))

def str2ints(myString):
    return map(lambda x: int(x), myString.split(","))

def webColorToVtkColor(string):
    red   = int(string[1:3], 16) / 255.
    green = int(string[3:5], 16) / 255.
    blue  = int(string[5:7], 16) / 255.
    return red, green, blue



class XML2VTK:
    def __init__ (self, topElement, basedir='', bonelengths=''):
        self.logger = logging.getLogger(name='XML2VTK')
        self.logger.debug('__init__()')
        self.actors = {}
        self.assemblies = {}
        self.glyphsources = {}
        self.lights = {}
        self.textures = {}
        self.bonelengths = bonelengths
        self.basedir = basedir

        self.namesToFunctions = {}
        self.namesToFunctions['Actor'] = self.Actor
        self.namesToFunctions['Assembly'] = self.Assembly
        self.namesToFunctions['BMPReader'] = self.BMPReader
        self.namesToFunctions['ConeSource'] = self.ConeSource
        self.namesToFunctions['ContourFilter'] = self.ContourFilter
        self.namesToFunctions['CubeSource'] = self.CubeSource
        self.namesToFunctions['CylinderSource'] = self.CylinderSource
        self.namesToFunctions['DiskSource'] = self.DiskSource
        self.namesToFunctions['DataSetMapper'] = self.DataSetMapper
        self.namesToFunctions['glyph'] = self.glyph # wrapper
        self.namesToFunctions['Glyph3D'] = self.Glyph3D
        self.namesToFunctions['GlyphSource2D'] = self.GlyphSource2D
        self.namesToFunctions['ImplicitModeller'] = self.ImplicitModeller
        self.namesToFunctions['ImplicitSum'] = self.ImplicitSum
        self.namesToFunctions['Light'] = self.Light
        self.namesToFunctions['PerlinNoise'] = self.PerlinNoise
        self.namesToFunctions['Plane'] = self.Plane
        self.namesToFunctions['PolyDataMapper'] = self.PolyDataMapper
        self.namesToFunctions['PolyDataNormals'] = self.PolyDataNormals
        self.namesToFunctions['PolyDataReader'] = self.PolyDataReader
        self.namesToFunctions['SampleFunction'] = self.SampleFunction
        self.namesToFunctions['SphereSource'] = self.SphereSource
        self.namesToFunctions['Texture'] = self.Texture
        self.namesToFunctions['TextureMapToPlane'] = self.TextureMapToPlane
        self.namesToFunctions['TextureMapToSphere'] = self.TextureMapToSphere
        self.namesToFunctions['Transform'] = self.Transform
        self.namesToFunctions['TransformPolyDataFilter'] = self.TransformPolyDataFilter
        self.namesToFunctions['TransformFilter'] = self.TransformFilter
        self.namesToFunctions['UnstructuredGridReader'] = self.UnstructuredGridReader

        if topElement.tag == "VTKpipelines":
            self.logger.debug('inside a <VTKpipelines> element')
            if 'bgcolor' in topElement.keys():
                self.bgcolor = webColorToVtkColor(topElement.get('bgcolor'))

            # All of these first-level elements get named and placed into
            # a python dictionary: 
            for (elemType, elemDict) in [('Texture', self.textures),
					 ('glyph', self.glyphsources),
					 ('Actor', self.actors),
					 ('Assembly', self.assemblies),
					 ('Light', self.lights)]:
                for subElement in topElement.findall(elemType):
                    if 'name' in subElement.keys():
                        name = subElement.get('name')
                        try:
                            elemDict[name] = self.namesToFunctions[subElement.tag](subElement)
                        except:
                            self.logger.error('Failed to create <%s> %s' % (elemType, name))
                    else:
                        self.logger.error('First-level <%s> must have a name attribute.' % elemType)

    # <glyph> is a wrapper for any kind of Algorithm-type data
    def glyph(self, currentElement):
        self.logger.debug('  inside a <glyph> element: "%s"' % currentElement.get('name'))
        algoData = ''
        # Datatype(s) I need for input:  Algorithm
        AlgorithmElement = ''
        for childElement in currentElement.getchildren():
            if childElement.tag in vtkTypes['Algorithm']:
                AlgorithmElement = childElement
        if AlgorithmElement != '':
            algoData = self.namesToFunctions[AlgorithmElement.tag](AlgorithmElement)
        else:
            self.logger.error('  .. <glyph> needs an Algorithm-type childElement')
        return algoData


    def Texture(self, currentElement):
        self.logger.debug('  inside a <Texture> element: "%s"' % currentElement.get('name'))
        texture = vtk.vtkTexture()

        # Datatype(s) I need for input: ImageReader
        ImageReaderNode = ''
        for childElement in currentElement.getchildren():
            if childElement.tag in vtkTypes['ImageReader']:
                ImageReaderNode = childElement
        if ImageReaderNode != '':
            imageReader = self.namesToFunctions[ImageReaderNode.tag](ImageReaderNode)
            try:
                texture.SetInputConnection(imageReader.GetOutputPort())
            except:
                self.logger.error('  .. <Texture> failed to SetInputConnection')
        else:
            self.logger.error('  .. <Texture> needs an ImageReader-type childElement.')

        if 'SetRepeat' in currentElement.keys():
            try:
                texture.SetRepeat(int( currentElement.get('SetRepeat')))
            except:
                self.logger.error('  .. <Texture> failed to SetRepeat')
        if 'SetInterpolate' in currentElement.keys():
            try:
                texture.SetInterpolate(int( currentElement.get('SetInterpolate')))
            except:
                self.logger.error('  .. <Texture> failed to SetInterpolate')
        return texture

    def Assembly(self, currentElement):
        self.logger.debug('  inside an <Assembly> element: "%s"' % currentElement.get('name'))
        assembly = vtk.vtkAssembly()
        if 'SetPosition' in currentElement.keys():
            try:
                assembly.SetPosition(coordsFromString(currentElement.get('SetPosition')))
            except:
                self.logger.error('  .. <Assembly> failed to SetPosition')
        if 'SetOrientation' in currentElement.keys():
            try:
                assembly.SetOrientation(coordsFromString(currentElement.get('SetOrientation')))
            except:
                self.logger.error('  .. <Assembly> failed to SetOrientation')
        for childElement in currentElement.getchildren():
            if childElement.tag in vtkTypes['Prop3D']:
                actor = self.namesToFunctions[childElement.tag](childElement)
                try:
                    assembly.AddPart(actor)
                except:
                    self.logger.error('  .. <Assembly> failed to AddPart (ie, probably failed to add a childElement <Actor>)')
        return assembly

    def BMPReader(self, currentElement):
        reader = vtk.vtkBMPReader()
        try:
            reader.SetFileName( os.path.join(self.basedir, currentElement.get('SetFileName')) )
        except:
            self.logger.error('  .. <BMPReader> failed to SetFileName')
        return reader
            
    def Actor(self, currentElement):
        self.logger.debug('  inside an <Actor> element: "%s"' % currentElement.get('name'))
        actor = vtk.vtkActor()

        # Datatype(s) I need for input: Mapper
        MapperElement = ''
        for childElement in currentElement.getchildren():
            if childElement.tag in vtkTypes['Mapper']:
                MapperElement = childElement
        if MapperElement != '':
            #self.logger.debug('  .. <Actor> setting mapper...')
            mapper = self.namesToFunctions[MapperElement.tag](MapperElement)
            try:
                actor.SetMapper(mapper)
            except:
                self.logger.error('  .. <Actor> failed to SetMapper')
        else:
            self.logger.error('  .. <Actor> needs a Mapper-type childElement')

        self.logger.debug('  .. <Actor> setting optional attributes...')
        actor.SetPickable(0)
        #if 'SetPickable' in currentElement.keys():
        #    actor.SetPickable( int(currentElement.get('SetPickable')) )
        if 'href' in currentElement.keys():
            actor.SetPickable(1)
            actor.href = currentElement.get('href')
        if 'SetPosition' in currentElement.keys():
            try:
                actor.SetPosition( coordsFromString(currentElement.get('SetPosition')) )
            except:
                self.logger.error("  .. <Actor> failed to SetPosition")
        if 'SetOrientation' in currentElement.keys():
            try:
                actor.SetOrientation( coordsFromString(currentElement.get('SetOrientation')) )
            except:
                self.logger.error("  .. <Actor> failed to SetOrientation")
        if 'SetScale' in currentElement.keys():
            try:
                actor.SetScale( coordsFromString(currentElement.get('SetScale')) )
            except:
                self.logger.error("  .. <Actor> failed to SetOrientation")
        if 'SetOpacity' in currentElement.keys():
            try:
                actor.GetProperty().SetOpacity( float(currentElement.get('SetOpacity')) )
            except:
                self.logger.error("  .. <Actor> failed to SetOpacity")
        if 'SetColor' in currentElement.keys():
            try:
                actor.GetProperty().SetColor( coordsFromString(currentElement.get('SetColor')) )
            except:
                self.logger.error("  .. <Actor> failed to SetColor")
        if 'color' in currentElement.keys(): # allow for Web colors
            try:
                actor.color = webColorToVtkColor(currentElement.get('color'))
                actor.GetProperty().SetColor(actor.color)
            except:
                self.logger.error("  .. <Actor> failed to set HTML-style color")
        if 'hovercolor' in currentElement.keys(): # allow for Web colors
            actor.hovercolor = webColorToVtkColor(currentElement.get('hovercolor'))
        if 'SetTexture' in currentElement.keys():
            textureName = currentElement.get('SetTexture')
            if textureName in self.textures:
                actor.SetTexture( self.textures[textureName] )
            else:
                self.logger.error("  .. <Actor> unknown texture: %s" % textureName)
        self.logger.debug('  .. <Actor> done setting optional attributes.')
        return actor

    def Light(self, currentElement):
        self.logger.debug('  inside a <Light> element: "%s"' % currentElement.get('name'))
        light = vtk.vtkLight()

        try:
            light.SetPosition( coordsFromString(currentElement.get('SetPosition')) )
        except:
            self.logger.error("  .. <Light> failed to SetPosition")
        try:
            light.SetFocalPoint( coordsFromString(currentElement.get('SetFocalPoint')) )
        except:
            self.logger.error("  .. <Light> failed to SetFocalPoint")
        if 'SetPositional' in currentElement.keys():
            try:
                light.SetPositional( int(currentElement.get('SetPositional')) )
            except:
                self.logger.error("  .. <Light> failed to SetPositional")
        if 'SetColor' in currentElement.keys():
            try:
                light.SetColor( coordsFromString(currentElement.get('SetColor')) )
            except:
                self.logger.error("  .. <Light> failed to SetColor")
        if 'color' in currentElement.keys():  # give people the option of using HTML-style color:
            try:
                light.SetColor( webColorToVtkColor(currentElement.get('color')) )
            except:
                self.logger.error("  .. <Light> failed to set HTML-style color")
        if 'SetConeAngle' in currentElement.keys():
            try:
                light.SetConeAngle( float(currentElement.get('SetConeAngle')) )
            except:
                self.logger.error("  .. <Light> failed to SetConeAngle")
        if 'SetIntensity' in currentElement.keys():
            try:
                light.SetIntensity( float(currentElement.get('SetIntensity')) )
            except:
                self.logger.error("  .. <Light> failed to SetIntensity")
        return light


    def DataSetMapper(self, currentElement):
        #self.logger.debug('  .. inside a <DataSetMapper>')
        mapper = vtk.vtkDataSetMapper()
        # Datatype(s) I need for input:  Algorithm
        AlgorithmElement = ''
        for childElement in currentElement.getchildren():
            if childElement.tag in vtkTypes['Algorithm']:
                AlgorithmElement = childElement
        if AlgorithmElement != '':
            #self.logger.debug('  .. <DataSetMapper> trying to get a dataset from a %s' % AlgorithmElement.tag)
            dataset = self.namesToFunctions[AlgorithmElement.tag](AlgorithmElement)
            try:
                mapper.SetInputConnection(dataset.GetOutputPort())
            except:
                self.logger.error("  .. <DataSetMapper> failed to SetInputConnection")
        else:
            self.logger.error('  .. <DataSetMapper> needs an Algorithm-type childElement')
        return mapper

    def GlyphSource2D(self, currentElement):
        gsource = vtk.vtkGlyphSource2D()
        #if 'SetGlyphType' in currentElement.keys():
        gsource.SetGlyphTypeToArrow ()
        if 'SetFilled' in currentElement.keys():
            try:
                gsource.SetFilled( int(currentElement.get('SetFilled')) )
            except:
                self.logger.error('  .. <GlyphSource2D> failed to SetFilled')
        if 'SetScale' in currentElement.keys():
            try:
                gsource.SetScale( float(currentElement.get('SetScale')) )
            except:
                self.logger.error('  .. <GlyphSource2D> failed to SetScale')
        return gsource

    def PolyDataMapper(self, currentElement):
        mapper = vtk.vtkPolyDataMapper()
        # Datatype(s) I need for input:  Algorithm
        AlgorithmElement = ''
        for childElement in currentElement.getchildren():
            if childElement.tag in vtkTypes['Algorithm']:
                AlgorithmElement = childElement
        if AlgorithmElement != '':
            dataset = self.namesToFunctions[AlgorithmElement.tag](AlgorithmElement)
            try:
                mapper.SetInputConnection(dataset.GetOutputPort())
            except:
                self.logger.error("  .. <PolyDataMapper> failed to SetInputConnection")
        else:
            self.logger.error('  .. <PolyDataMapper> needs an Algorithm-type childElement')
        return mapper

    def TransformPolyDataFilter(self, currentElement):
        transFilter = vtk.vtkTransformPolyDataFilter()
        # Datatype(s) I need for input:  Algorithm, LinearTransform
        AlgorithmElement = ''
        TransformElement = ''
        for childElement in currentElement.getchildren():
            if childElement.tag in vtkTypes['Algorithm']:
                AlgorithmElement = childElement
            if childElement.tag in vtkTypes['LinearTransform']:
                TransformElement = childElement
        if AlgorithmElement != '':
            dataset = self.namesToFunctions[AlgorithmElement.tag](AlgorithmElement)
            try:
                transFilter.SetInputConnection(dataset.GetOutputPort())
            except:
                self.logger.error('  .. <TransformPolyDataFilter> failed to SetInputConnection')
        else:
            self.logger.error('  .. <TransformPolyDataFilter> needs an Algorithm-type childElement')
        if TransformElement != '':
            transform = self.namesToFunctions[TransformElement.tag](TransformElement)
            try:
                transFilter.SetTransform(transform)
            except:
                self.logger.error('  .. <TransformPolyDataFilter> failed to SetTransform')
        else:
            self.logger.error('<TransformPolyDataFilter> needs an Transform-type childElement')
        return transFilter

    def TransformFilter(self, currentElement):
        transFilter = vtk.vtkTransformFilter()
        # Datatype(s) I need for input:  Algorithm, LinearTransform
        AlgorithmElement = ''
        TransformElement = ''
        for childElement in currentElement.getchildren():
            if childElement.tag in vtkTypes['Algorithm']:
                AlgorithmElement = childElement
            if childElement.tag in vtkTypes['LinearTransform']:
                TransformElement = childElement
        if AlgorithmElement != '':
            dataset = self.namesToFunctions[AlgorithmElement.tag](AlgorithmElement)
            try:
                transFilter.SetInputConnection(dataset.GetOutputPort())
            except:
                self.logger.error('  .. <TransformFilter> failed to SetInputConnection')
        else:
            self.logger.error('  .. <TransformFilter> needs an Algorithm-type childElement')
        if TransformElement != '':
            transform = self.namesToFunctions[TransformElement.tag](TransformElement)
            try:
                transFilter.SetTransform(transform)
            except:
                self.logger.error('  .. <TransformFilter> failed to SetTransform')
        else:
            self.logger.error('<TransformFilter> needs an Transform-type childElement')
        return transFilter


    def Transform(self, currentElement):
        transform = vtk.vtkTransform()
        # TODO:  preserve the order of rotations...
        if 'RotateZ' in currentElement.keys():
            try:
                transform.RotateZ( float(currentElement.get('RotateZ')) )
            except:
                self.logger.error("  .. <Transform> failed to RotateZ")
        if 'RotateX' in currentElement.keys():
            try:
                transform.RotateX( float(currentElement.get('RotateX')) )
            except:
                self.logger.error("  .. <Transform> failed to RotateX")
        if 'RotateY' in currentElement.keys():
            try:
                transform.RotateY( float(currentElement.get('RotateY')) )
            except:
                self.logger.error("  .. <Transform> failed to RotateY")
        if 'Translate' in currentElement.keys():
            try:
                transform.Translate( coordsFromString(currentElement.get('Translate')) )
            except:
                self.logger.error('  .. <Transform> failed to Translate')
        if 'boneBuild' in currentElement.keys():
            try:
                transform.Translate(0.0, self.bonelengths[currentElement.get('boneBuild')] / 2., 0.0 )
            except:
                self.logger.error('  .. <Transform> failed to Translate from boneBuild')
        if 'Scale' in currentElement.keys():
            try:
                transform.Scale( coordsFromString(currentElement.get('Scale')))
            except:
                self.logger.error('  .. <Transform> failed to Scale')
        return transform


    def CylinderSource(self, currentElement):
        source = vtk.vtkCylinderSource()
        try:
            source.SetRadius( float(currentElement.get('SetRadius')) )
        except:
            self.logger.error('  .. <CylinderSource> failed to SetRadius')
        if 'SetHeight' in currentElement.keys():
            try:
                source.SetHeight( float(currentElement.get('SetHeight')) )
            except:
                self.logger.error('  .. <CylinderSource> failed to SetHeight')
        if 'boneLength' in currentElement.keys():
            try:
                source.SetHeight( self.bonelengths[currentElement.get('boneLength')] )
            except:
                self.logger.error('  .. <CylinderSource> failed to SetHeight from boneLength')
        if 'SetResolution' in currentElement.keys():
            try:
                source.SetResolution( int(currentElement.get('SetResolution')) )
            except:
                self.logger.error('  .. <CylinderSource> failed to SetResolution')
        if 'SetCapping' in currentElement.keys():
            try:
                source.SetCapping( int(currentElement.get('SetCapping')) )
            except:
                self.logger.error('  .. <CylinderSource> failed to SetCapping')
        return source

    def DiskSource(self, currentElement):
        source = vtk.vtkDiskSource()
        try:
            source.SetInnerRadius( float(currentElement.get('SetInnerRadius')) )
        except:
            self.logger.error('  .. <DiskSource> failed to SetInnerRadius')
        try:
            source.SetOuterRadius( float(currentElement.get('SetOuterRadius')) )
        except:
            self.logger.error('  .. <DiskSource> failed to SetOuterRadius')
        if 'SetRadialResolution' in currentElement.keys():
            try:
                source.SetRadialResolution( int(currentElement.get('SetRadialResolution')) )
            except:
                self.logger.error('  .. <CylinderSource> failed to SetRadialResolution')
        if 'SetCircumferentialResolution' in currentElement.keys():
            try:
                source.SetCircumferentialResolution( int(currentElement.get('SetCircumferentialResolution')) )
            except:
                self.logger.error('  .. <CylinderSource> failed to SetCircumferentialResolution')
        return source



    def ConeSource(self, currentElement):
        source = vtk.vtkConeSource()
        try:
            source.SetHeight( float(currentElement.get('SetHeight')) )
        except:
            self.logger.error('  .. <ConeSource> failed to SetHeight')
        try:
            source.SetRadius( float(currentElement.get('SetRadius')) )
        except:
            self.logger.error('  .. <ConeSource> failed to SetRadius')
        if 'SetResolution' in currentElement.keys():
            try:
                source.SetResolution( int(currentElement.get('SetResolution')) )
            except:
                self.logger.error('  .. <ConeSource> failed to SetResolution')
        if 'SetCenter' in currentElement.keys():
            try:
                source.SetCenter( coordsFromString(currentElement.get('SetCenter')) )
            except:
                self.logger.error('  .. <ConeSource> failed to SetCenter')
        if 'SetDirection' in currentElement.keys():
            try:
                source.SetDirection( coordsFromString(currentElement.get('SetDirection')) )
            except:
                self.logger.error('  .. <ConeSource> failed to SetDirection')
        return source

    def CubeSource(self, currentElement):
        source = vtk.vtkCubeSource()
        try:
            source.SetXLength( float(currentElement.get('SetXLength')) )
        except:
            self.logger.error('  .. <CubeSource> failed to SetXLength')
        try:
            source.SetYLength( float(currentElement.get('SetYLength')) )
        except:
            self.logger.error('  .. <CubeSource> failed to SetYLength')
        try:
            source.SetZLength( float(currentElement.get('SetZLength')) )
        except:
            self.logger.error('  .. <CubeSource> failed to SetZLength')
        return source

    def SphereSource(self, currentElement):
        source = vtk.vtkSphereSource()
        try:
            source.SetRadius( float(currentElement.get('SetRadius')) )
        except:
            self.logger.error('  .. <SphereSource> failed to SetRadius')
        if 'SetThetaResolution' in currentElement.keys():
            try:
                source.SetThetaResolution( int(currentElement.get('SetThetaResolution')) )
            except:
                self.logger.error('  .. <SphereSource> failed to SetThetaResolution')
        if 'SetPhiResolution' in currentElement.keys():
            try:
                source.SetPhiResolution( int(currentElement.get('SetPhiResolution')) )
            except:
                self.logger.error('  .. <SphereSource> failed to SetPhiResolution')
        if 'SetStartTheta' in currentElement.keys():
            try:
                source.SetStartTheta( float(currentElement.get('SetStartTheta')) )
            except:
                self.logger.error('  .. <SphereSource> failed to SetStartTheta')
        if 'SetEndTheta' in currentElement.keys():
            try:
                source.SetEndTheta( float(currentElement.get('SetEndTheta')) )
            except:
                self.logger.error('  .. <SphereSource> failed to SetEndTheta')
        return source

    def UnstructuredGridReader(self, currentElement):
        reader = vtk.vtkUnstructuredGridReader()
        try:
            reader.SetFileName(os.path.join(self.basedir, currentElement.get('SetFileName')))
        except:
            self.logger.error('  .. <UnstructuredGridReader> failed to SetFileName')
        if 'SetVectorsName' in currentElement.keys():
            try:
                reader.SetVectorsName( currentElement.get('SetVectorsName') )
            except:
                self.logger.error('  .. <UnstructuredGridReader> failed to SetVectorsName')
        return reader

    def PolyDataReader(self, currentElement):
        reader = vtk.vtkPolyDataReader()
        try:
            reader.SetFileName(os.path.join(self.basedir, currentElement.get('SetFileName')))
        except:
            self.logger.error('  .. <PolyDataReader> failed to SetFileName')
        return reader

    def ImplicitModeller(self, currentElement):
        impModeller = vtk.vtkImplicitModeller()
        # Datatype(s) I need for input:  Algorithm
        AlgorithmElement = ''
        for childElement in currentElement.getchildren():
            if childElement.tag in vtkTypes['Algorithm']:
                AlgorithmElement = childElement
        if AlgorithmElement != '':
            dataset = self.namesToFunctions[AlgorithmElement.tag](AlgorithmElement)
            self.logger.debug("  .. <ImplicitModeller> trying to SetInputConnection")
            try:
                impModeller.SetInputConnection(dataset.GetOutputPort())
            except:
                self.logger.error("  .. <ImplicitModeller> failed to SetInputConnection")
        else:
            self.logger.error('  .. <ImplicitModeller> needs an Algorithm-type childElement')
        if 'SetSampleDimensions' in currentElement.keys():
            self.logger.debug('  .. <ImplicitModeller> trying to SetSampleDimensions')
            try:
                impModeller.SetSampleDimensions( str2ints(currentElement.get('SetSampleDimensions')) )
            except:
                self.logger.error('  .. <ImplicitModeller> failed to SetSampleDimensions')
        if 'SetModelBounds' in currentElement.keys():
            self.logger.debug('  .. <ImplicitModeller> trying to SetModelBounds')
            try:
                impModeller.SetModelBounds( str2floats(currentElement.get('SetModelBounds')) )
            except:
                self.logger.error('  .. <ImplicitModeller> failed to SetModelBounds')
        if 'SetMaximumDistance' in currentElement.keys():
            self.logger.debug('  .. <ImplicitModeller> trying to SetMaximumDistance')
            try:
                impModeller.SetMaximumDistance( float(currentElement.get('SetMaximumDistance')) )
            except:
                self.logger.error('  .. <ImplicitModeller> failed to SetMaximumDistance')
        return impModeller

    def ContourFilter(self, currentElement):
        contFilt = vtk.vtkContourFilter()
        # Datatype(s) I need for input:  Algorithm
        AlgorithmElement = ''
        for childElement in currentElement.getchildren():
            if childElement.tag in vtkTypes['Algorithm']:
                AlgorithmElement = childElement
        if AlgorithmElement != '':
            dataset = self.namesToFunctions[AlgorithmElement.tag](AlgorithmElement)
            try:
                contFilt.SetInputConnection(dataset.GetOutputPort())
            except:
                self.logger.error("  .. <ContourFilter> failed to SetInputConnection")
        else:
            self.logger.error('  .. <ContourFilter> needs an Algorithm-type childElement')
        #if 'SetValue' in currentElement.keys():
        #    self.logger.debug('  .. <ContourFilter> trying to SetValue')
        #    try:
        #        contFilt.SetValue( str2floats(currentElement.get('SetValue')) )
        #    except:
        #        self.logger.error('  .. <ContourFilter> failed to SetValue')
        contFilt.SetValue(0, 0.25)
        return contFilt

    def Glyph3D(self, currentElement):
        glyph = vtk.vtkGlyph3D()
        # Datatype(s) I need for input: Algorithm
        AlgorithmElement = ''
        for childElement in currentElement.getchildren():
            if childElement.tag in vtkTypes['Algorithm']:
                AlgorithmElement = childElement
        if AlgorithmElement != '':
            dataset = self.namesToFunctions[AlgorithmElement.tag](AlgorithmElement)
            try:
                glyph.SetInputConnection(dataset.GetOutputPort())
            except:
                self.logger.error('  .. <Glyph3D> failed to SetInputConnection')
        else:
            self.logger.error('  .. <Glyph3D> needs an Algorithm-type childElement')
        if 'SetSource' in currentElement.keys():
            gsourceName = currentElement.get('SetSource')
            try:
                self.logger.debug('  .. <Glyph3D> SetSource(%s)' % gsourceName)
                glyph.SetSource( self.glyphsources[gsourceName].GetOutput() )
            except:
                self.logger.error('  .. <Glyph3D> failed to SetSource')
        glyph.SetScaleModeToScaleByVector ()
        glyph.SetColorModeToColorByVector ()
        glyph.SetRange(0.0, 0.11445075055913652)
        glyph.SetScaleFactor(3.0)

        return glyph


    def TextureMapToPlane(self, currentElement):
        tmapper = vtk.vtkTextureMapToPlane()
        # Datatype(s) I need for input:  Algorithm
        AlgorithmElement = ''
        for childElement in currentElement.getchildren():
            if childElement.tag in vtkTypes['Algorithm']:
                AlgorithmElement = childElement
        if AlgorithmElement != '':
            dataset = self.namesToFunctions[AlgorithmElement.tag](AlgorithmElement)
            try:
                tmapper.SetInputConnection(dataset.GetOutputPort())
            except:
                self.logger.error('  .. <TextureMapToPlane> failed to SetInputConnection')
        else:
            self.logger.error('  .. <TextureMapToPlane> needs an Algorithm-type childElement')
        if 'SetOrigin' in currentElement.keys():
            try:
                tmapper.SetOrigin( coordsFromString(currentElement.get('SetOrigin')) )
            except:
                self.logger.error('  .. <TextureMapToPlane> failed to SetOrigin')
        if 'SetPoint1' in currentElement.keys():
            try:
                tmapper.SetPoint1( coordsFromString(currentElement.get('SetPoint1')) )
            except:
                self.logger.error('  .. <TextureMapToPlane> failed to SetPoint1')
        if 'SetPoint2' in currentElement.keys():
            try:
                tmapper.SetPoint2( coordsFromString(currentElement.get('SetPoint2')) )
            except:
                self.logger.error('  .. <TextureMapToPlane> failed to SetPoint2')
        return tmapper

    def TextureMapToSphere(self, currentElement):
        tmapper = vtk.vtkTextureMapToSphere()
        # Datatype(s) I need for input:  Algorithm
        AlgorithmElement = ''
        for childElement in currentElement.getchildren():
            if childElement.tag in vtkTypes['Algorithm']:
                AlgorithmElement = childElement
        if AlgorithmElement != '':
            dataset = self.namesToFunctions[childElement.tag](childElement)
            try:
                tmapper.SetInputConnection(dataset.GetOutputPort())
            except:
                self.logger.error('  .. <TextureMapToSphere> failed to SetInputConnection')
            if 'SetPreventSeam' in currentElement.keys():
                try:
                    tmapper.SetPreventSeam( int(currentElement.get('SetPreventSeam')) )
                except:
                    self.logger.error('  .. <TextureMapToSphere> failed to SetPreventSeam')
        else:
            self.logger.error('  .. <TextureMapToSphere> needs an Algorithm-type childnode')
        return tmapper

    def PerlinNoise(self, currentElement):
        pNoise = vtk.vtkPerlinNoise()
        try:
            pNoise.SetFrequency( coordsFromString(currentElement.get('SetFrequency')) )
        except:
            self.logger.error('  .. <PelinNoise> failed to SetFrequency')
        if 'SetThetaResolution' in currentElement.keys():
            try:
                pNoise.SetThetaResolution( coordsFromString(currentElement.get('SetPhase')) )
            except:
                self.logger.error('  .. <PelinNoise> failed to SetPhase')
        return pNoise

    def ImplicitSum(self, currentElement):
        impSum = vtk.vtkImplicitSum()
        impSum.SetNormalizeByWeight(1)
        for childElement in currentElement.getchildren():
            if childElement.tag in vtkTypes['ImplicitFunction']:
                childFunc = self.namesToFunctions[childElement.tag](childElement)
                if 'weight' in childElement.keys():
                    childWeight = float(childElement.get('weight'))
                else:
                    childWeight = 1.
                self.logger.error('  .. <ImplicitSum> trying to AddFunction')
                try:
                    impSum.AddFunction(childFunc, childWeight)
                except:
                    self.logger.error('  .. <ImplicitSum> failed to AddFunction')
        return impSum

    def SampleFunction(self, currentElement):
        sampFunc = vtk.vtkSampleFunction()
        # Datatype(s) I need for input:  Algorithm
        AlgorithmElement = ''
        for childElement in currentElement.getchildren():
            if childElement.tag in vtkTypes['Algorithm']:
                AlgorithmElement = childElement
        if AlgorithmElement != '':
            dataset = self.namesToFunctions[AlgorithmElement.tag](AlgorithmElement)
            self.logger.debug('  .. <SampleFunction> trying to SetImplicitFunction.')
            try:
                sampFunc.SetImplicitFunction(dataset)
            except:
                self.logger.error('  .. <SampleFunction> failed to SetImplicitFunction.')
        if 'SetSampleDimensions' in currentElement.keys():
            self.logger.debug('  .. <SampleFunction> trying to SetSampleDimensions')
            try:
                sampFunc.SetSampleDimensions( str2ints(currentElement.get('SetSampleDimensions')) )
            except:
                self.logger.error('  .. <SampleFunction> failed to SetSampleDimensions')
        if 'SetModelBounds' in currentElement.keys():
            self.logger.debug('  .. <SampleFunction> trying to SetModelBounds')
            try:
                sampFunc.SetModelBounds( str2floats(currentElement.get('SetModelBounds')) )
            except:
                self.logger.error('  .. <SampleFunction> failed to SetModelBounds')
        sampFunc.ComputeNormalsOff()
        return sampFunc

    def PolyDataNormals(self, currentElement):
        pDatNorms = vtk.vtkPolyDataNormals()
        # Datatype(s) I need for input:  Algorithm
        AlgorithmElement = ''
        for childElement in currentElement.getchildren():
            if childElement.tag in vtkTypes['Algorithm']:
                AlgorithmElement = childElement
        if AlgorithmElement != '':
            dataset = self.namesToFunctions[childElement.tag](childElement)
            self.logger.error('  .. <PolyDataNormals> trying to to SetInputConnection.')
            try:
                pDatNorms.SetInputConnection(dataset.GetOutputPort())
            except:
                self.logger.error('  .. <PolyDataNormals> failed to SetInputConnection.')
            if 'SetFeatureAngle' in currentElement.keys():
                self.logger.debug('  .. <PolyDataNormals> trying to SetFeatureAngle')
                try:
                    pDatNorms.SetFeatureAngle( float(currentElement.get('SetFeatureAngle')) )
                except:
                    self.logger.error('  .. <PolyDataNormals> failed to SetFeatureAngle')
        return pDatNorms

    def Plane(self, currentElement):
        aPlane = vtk.vtkPlane()
        return aPlane


#class AvatarReader:
#    def __init__ (self, basedir, bonelengths = ''):
#        self.basedir = basedir + "/"
#        self.bonelengths = bonelengths
#        fd = open(self.basedir + "index.xml", 'r')
#        XMLstring = fd.read()
#        fd.close()
#        xmlConverter = XML2VTK(XMLstring, bonelengths = self.bonelengths)
#
#        self.actors = xmlConverter.actors
#        self.assemblies = xmlConverter.assemblies
#
#        # Bind everything into a single object for the viewer:
#        self.assembly = vtk.vtkAssembly()
#        for i in self.actors:
#            self.assembly.AddPart(self.actors[i])
#        for i in self.assemblies:
#            self.assembly.AddPart(self.assemblies[i])

class MapReader:
    def __init__ (self, mapname):
        self.logger = logging.getLogger(name = "MapReader")
        self.logger.debug('Attempting to load map: %s' % mapname + "/index.xml")
        self.mapname = mapname
        self.basedir = os.path.join(jvDataDir, 'Maps', mapname)
        filename = os.path.join(jvDataDir, "Maps", mapname, "index.xml")
        fd = open(filename, 'r')
        XMLstring = fd.read()
        fd.close()
        self.logger.debug("Attempting to parse XML...")
        try:
            topElement = ET.fromstring(XMLstring)
        except xml.parsers.expat.ExpatError as err:
            self.logger.error("Failed to parse file: %s" % mapname + "/index.xml:")
            self.logger.error("  ExpatError: %s" % err)
        xmlConverter = XML2VTK(topElement, basedir=self.basedir)

        self.textures = xmlConverter.textures
        self.actors = xmlConverter.actors
        self.assemblies = xmlConverter.assemblies
        self.lights = xmlConverter.lights
        self.glyphsources = xmlConverter.glyphsources
        try:
            self.bgcolor = xmlConverter.bgcolor
        except:
            pass


